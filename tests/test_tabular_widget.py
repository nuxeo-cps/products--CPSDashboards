# (C) Copyright 2006 Nuxeo SAS <http://nuxeo.com>
# Author: Georges Racinet <gracinet@nuxeo.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#

#$Id$

# testing module and harness

import unittest
from zope.testing import doctest

from Products.CPSDefault.tests.CPSTestCase import CPSTestCase

from Products.CPSDashboards.tests.layer import CPSDashboardsLayer
from Products.CPSSchemas.tests.testWidgets import FakeDataStructure

# things to be tested
from Products.CMFCore.utils import getToolByName
from Products.CPSSchemas.DataStructure import DataStructure
from Products.CPSSchemas.DataModel import DataModel
from Products.CPSSchemas.Widget import widgetRegistry
from Products.CPSDocument.FlexibleTypeInformation import FlexibleTypeInformation

from Products.CPSDashboards.widgets.tabular import FakeRequestWithCookies
from Products.CPSDashboards.tests.widgets import TestingTabularWidget
from Products.CPSDashboards.widgets.foldercontents import FolderContentsWidget
from Products.CPSDashboards.widgets.dirsearch import DirectoryTabularWidget


class CustomMethods:
    """ A mixin that provides custom render method with logging.

    XXX Tests have to set the 'render_method' attribute of widget to
    'widget_render_logging'
    """

    # attributes for introspection after method calls
    last_render_call = None
    passed_rows = None
    passed_columns = None
    passed_batching_info = None

    def getMethodContext(self, datastructure):
        return self

    def clearHistory(self):
        self.last_render_call = None

    def layout_default_view(self, layout=None, **kw):
        self.last_called = 'view'
        return '|'.join([row[0]['widget_rendered']
                          for row in layout['rows']]
                         )
    def widget_render_logging(self, columns=None,
                             rows=None,
                             batching_info=None, **kw):
        # deepcopy would not work
        # (Can't pickle objects in acquisition wrappers.)
        self.passed_columns = columns
        self.passed_rows = rows
        self.passed_batching_info = batching_info

class TestingTabularWidgetCustomMethods(CustomMethods, TestingTabularWidget):
    pass


class IntegrationTestCase(CPSTestCase):

    layer = CPSDashboardsLayer

    def afterSetUp(self):
        self.login('manager')

        # a common datastructure for portlet widget tests
        ptltool = self.portal.portal_cpsportlets
        self.ptl_id = ptltool.createPortlet(ptype_id='Test Tabular Portlet',
                                       context=self.portal,
                                       slot='slot',
                                       order=1)
        portlets_container = ptltool.getPortletContainer(
            context=self.portal)
        portlet = portlets_container.getPortletById(self.ptl_id)
        self.portlet = portlet
        dm = self.portlet.getTypeInfo().getDataModel(portlet, context=portlet)
        self.ds = DataStructure(datamodel=dm)

        self.afterAfterSetUp()

    def beforeTearDown(self):
        ## TODO: remove portlet
        pass

#
# Generic Tabular Widget
#

class IntegrationTestTabularPortlet(IntegrationTestCase):

    def afterAfterSetUp(self):
        # a portlet widget with custom rendering methods
        self.widget = TestingTabularWidgetCustomMethods(
            'the_id_custom').__of__(self.portal)
        self.widget.manage_changeProperties(row_layout='test_row')

    def test_widget_registration(self):
        self.assert_(
            'Testing Tabular Widget' in widgetRegistry.listWidgetMetaTypes())

    def test_layer(self):
        # some of these can be discarded to get more flexibility back
        layout_tool = self.portal.portal_layouts
        ptl_layout = getattr(layout_tool, 'test_portlet', None)
        self.failIf(ptl_layout is None)

        ptl_wi = getattr(ptl_layout, 'w__portlet', None)
        self.failIf(ptl_wi is None)
        self.assertEquals(ptl_wi.row_layout, 'test_row')

    def test_render_layout_default_view(self):
        # layout render context will be the usual one
        widget = TestingTabularWidget('the_id')
        widget.manage_changeProperties(row_layout='test_row')

        rendered = widget.render('view', self.ds)

    def test_render_view(self):
        rendered = self.widget.render('view', self.ds)
        self.assertEquals(rendered.split('\n'), [
            'Title 1|<div class="ddefault">Pending</div>',
            'Title 2|<div class="ddefault">Rejected</div>',
            ])

    def test_vidget_render_method(self):
        # call the widget with our testing render_method
        self.widget.render_method = 'widget_render_logging'
        rendered = self.widget.render('view', self.ds)

        # retrieved what was passed to the render method
        columns = self.widget.passed_columns
        rows = self.widget.passed_rows

        # rows hold the rendering of each item
        self.assert_(rows[0].find('Title 1') != -1)
        self.assert_(rows[1].find('Title 2') != -1)

        # columns hold the widget objects and more info
        # see also doctest.
        self.assert_(columns[0][0].meta_type == 'String Widget')
        self.assert_(columns[0][0].getId() == 'w__Title')

        self.assert_(columns[1][0].meta_type == 'Text Widget')
        self.assert_(columns[1][0].getId() == 'w__Content')

    def test_not_from_CPSDocument(self):
        # use-case: global search form with a tabular widget
        dm = DataModel({}, [], proxy=self.portal, context=self.portal)
        ds = DataStructure(datamodel=dm)
        rendered = self.widget.render('view', ds)
        self.assertEquals(rendered.split('\n'), [
            'Title 1|<div class="ddefault">Pending</div>',
            'Title 2|<div class="ddefault">Rejected</div>',
            ])

    def test_getActions(self):
        # don't fail if no action from the right category
        self.widget.actions_category = "won't exist, ever"
        self.assertEquals(self.widget.getActions(self.ds), [])

    def test_render_batching_info(self):
        self.widget.manage_changeProperties(items_per_page=5,
                                            batching_gadget_pages=2)

        # batching info is fetched by the tabular's prepare() method
        widget_in_form = self.widget.getHtmlWidgetId()
        self.widget.REQUEST = FakeRequestWithCookies(**{widget_in_form:4})
        self.widget.prepare(self.ds)

        # enable batching (specific to testing widget)
        self.ds['longbrains'] = True

        # enable logging of passed params
        self.widget.render_method = 'widget_render_logging'

        rendered = self.widget.render('view', self.ds)

        # extraction and assertions
        b_info = self.widget.passed_batching_info
        self.failIf(b_info is None) # should happen when there's one page only
        self.assertEquals(b_info['current_page'], 4)
        self.assertEquals(b_info['nb_pages'], 7) #  31 results
        self.assertEquals(b_info['form_key'], widget_in_form)
        self.assertEquals(b_info['linked_pages'], [2, 3, 4, 5, 6])

#
# Sub classes
#

class TestingFolderContentsWidget(CustomMethods,
                                  FolderContentsWidget):
    pass


class IntegrationTestFolderContentsPortlet(IntegrationTestCase):

    def afterAfterSetUp(self):
        self.widget = TestingFolderContentsWidget('the widget').__of__(self.portal)
        self.widget.manage_changeProperties(row_layout='test_row',
                                            render_method='')

    def test_widget_registration(self):
        self.assert_(
            'Folder Contents Widget' in widgetRegistry.listWidgetMetaTypes())

    def test_foldercontents(self):
        # creating some content to list
        wftool = self.portal.portal_workflow
        container = self.portal.workspaces
        item1 = wftool.invokeFactoryFor(container, 'News Item', 'item1',
                                        Title='Title 1',
                                        content='content 1')

        item2 = wftool.invokeFactoryFor(container, 'News Item', 'item2',
                                        Title='Title 2',
                                        content='content 2')

        rendered = self.widget.render('view', self.ds, context_obj=container)
        self.assertEquals(rendered.split('\n'), [
            'Title 1|<div class="ddefault">content 1</div>',
            'Title 2|<div class="ddefault">content 2</div>',
            ])

#
# Sub classes
#

class TestingDirectoryTabularWidget(CustomMethods,
                                    DirectoryTabularWidget,
                                    TestingTabularWidget):
    pass


class IntegrationTestDirectoryTabularWidget(IntegrationTestCase):

    def afterAfterSetUp(self):
        self.widget = TestingDirectoryTabularWidget('the widget').__of__(self.portal)
        self.widget.manage_changeProperties(row_layout='test_dir_row',
                                            render_method='',
                                            directory='members')
        dtool = getToolByName(self.portal, 'portal_directories')
        self.dir = dtool.members
        for i in range(3):
            self.dir._createEntry({'id': 'test_dirtab%d' % i, 'sn': 'dirtab'})

    def beforeTearDown(self):
        for i in range(3):
            self.dir._deleteEntry('test_dirtab%d' % i)
        IntegrationTestCase.beforeTearDown(self)

    def test_widget_registration(self):
        self.assert_(
            'Directory Tabular Widget' in widgetRegistry.listWidgetMetaTypes())

    def test_dirsearch(self):
        self.widget.updateFilters(self.ds, id='test_dirtab')
        rendered = self.widget.render('view', self.ds)
        self.assertEquals(rendered.split('\n'), [
            'test_dirtab0|dirtab',
            'test_dirtab1|dirtab',
            'test_dirtab2|dirtab',
            ])


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(IntegrationTestTabularPortlet),
        unittest.makeSuite(IntegrationTestFolderContentsPortlet),
        unittest.makeSuite(IntegrationTestDirectoryTabularWidget),
        doctest.DocTestSuite('Products.CPSDashboards.widgets.tabular'),
        doctest.DocFileTest('doc/developer/tabular_widget.txt',
                            package='Products.CPSDashboards'),
        ))
