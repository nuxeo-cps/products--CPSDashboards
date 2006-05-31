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
# $Id$


""" Directory Tabular Widget. """

from Globals import InitializeClass
from AccessControl import Unauthorized

from Products.CMFCore.utils import _checkPermission, getToolByName
from Products.CMFCore.permissions import View, ListFolderContents

from Products.CPSSchemas.Widget import CPSWidget
from Products.CPSSchemas.Widget import widgetRegistry
from Products.CPSSchemas.DataModel import DataModel
from Products.CPSSchemas.DataStructure import DataStructure
from Products.CPSSchemas.BasicWidgets import renderHtmlTag

from Products.CPSCourrier.braindatamodel import BrainDataModel
from Products.CPSCourrier.widgets.tabular import TabularWidget


class DirectoryTabularWidget(TabularWidget):
    """ A widget that renders a search form or search results for directories.

    >>> DirectoryTabularWidget('the_id')
    <DirectoryTabularWidget at the_id>
    """

    meta_type = 'Directory Tabular Widget'

    render_method = 'widget_tabular_render'

    _properties=TabularWidget._properties + (
        {'id': 'directory', 'type': 'string', 'mode': 'w',
         'label': 'The directory to search in'},)

    directory = ''

    def layout_row_view(self, layout=None, **kw):
        """Render method for rows layouts in 'view' mode.
        """

        if layout is None:
            raise ValueError("Computed layout is None")
        cells = (row[0] for row in layout['rows'])
        tags = (renderHtmlTag('td',
                              css_class=cell.get('widget_css_class'),
                              contents=cell['widget_rendered'],
                              )
                for cell in cells)
        return ''.join(tags)

    def getMethodContext(self, datastructure):
        return self

    def listRowDataStructures(self, datastructure, layout, filters=None, **kw):
        """Return datastructures filled with search results meta-data

        Currently, this will give an iterator on the full entry datamodels.
        It would be much better to have
        """

        if filters is None:
            raise ValueError('Filters is None')

        query = filters

        dtool = getToolByName(self, 'portal_directories')
        cpsdir = dtool[self.directory]

        entries = cpsdir.searchEntries(**query) # checks security
        (b_page, b_start, b_size) = self.getBatchParams(datastructure,
                                                        filters=filters)
        nb_pages = self.getNbPages(len(entries), b_size)
        entries = entries[b_start:b_start+b_size]

        dms = (cpsdir._getDataModel(id) for id in entries)
        return ((self.prepareRowDataStructure(layout,
                                              DataStructure(datamodel=dm))
                 for dm in dms),
                b_page, nb_pages)

InitializeClass(DirectoryTabularWidget)

widgetRegistry.register(DirectoryTabularWidget)
