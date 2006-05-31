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

import unittest
from zope.testing import doctest
from Products.CPSDefault.tests.CPSTestCase import CPSTestCase


from Products.CMFCore.utils import getToolByName
from Products.CPSSchemas.DataModel import DataModel
from Products.CPSSchemas.DataStructure import DataStructure

from Products.CPSCourrier.widgets.row_widgets import CPSUsersWithRolesWidget

class TestUsersWithRolesWidget(CPSTestCase):

    def afterSetUp(self):
        self.login('manager')
        self.dtool = getToolByName(self.portal, 'portal_directories')
        self.mdir = mdir = self.dtool.members
        mdir._createEntry({'id': 'user_roleswidget',
                           'sn': 'Roles Tester',
                           'roles' : ('Member'),
                           })
        gdir = self.dtool.groups
        gdir._createEntry({'group': 'group_roleswidget'})
        wftool = getToolByName(self.portal, 'portal_workflow')
        ws = self.portal.workspaces
        wftool.invokeFactoryFor(ws, 'Workspace',
                                'test_user_roles_widget')
        self.folder = ws.test_user_roles_widget
        self.widget = CPSUsersWithRolesWidget('the_wid').__of__(self.portal)

    def beforeTearDown(self):
        self.dtool.members._deleteEntry('user_roleswidget')
        self.dtool.groups._deleteEntry('group_roleswidget')

    def test_prepare(self):
        self.widget.merge_roles = True
        self.folder.manage_setLocalRoles('user_roleswidget', ['TestingRole'])
        dm = DataModel(None, proxy=self.folder)

        # Our test user matches
        ds = DataStructure(datamodel=dm)
        self.widget.roles = ['TestingRole', 'OtherRole']
        self.widget.prepare(ds)
        self.assert_('the_wid' in ds)
        self.assertEquals(ds['the_wid'], ['Roles Tester'])

        # Behavior when no user matches
        ds = DataStructure(datamodel=dm)
        self.widget.roles = ['No such Role']
        self.widget.prepare(ds)
        self.assert_('the_wid' in ds)
        self.assertEquals(ds['the_wid'], [])


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TestUsersWithRolesWidget),
        doctest.DocFileTest('doc/developer/row_widgets.txt',
                            package='Products.CPSCourrier'),
        ))
