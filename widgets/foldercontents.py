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


""" Folder Contents Portlet Widgets. """

from zLOG import LOG, DEBUG
from Globals import InitializeClass
from AccessControl import Unauthorized

from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.permissions import View, ListFolderContents

from Products.CPSSchemas.Widget import CPSWidget
from Products.CPSSchemas.Widget import widgetRegistry
from Products.CPSSchemas.DataModel import DataModel
from Products.CPSSchemas.DataStructure import DataStructure
from Products.CPSSchemas.BasicWidgets import renderHtmlTag
from Products.CPSSkins.cpsskins_utils import serializeForCookie

from Products.CPSCourrier.widgets.tabular import TabularWidget

_missed = object()

class FolderContentsWidget(TabularWidget):
    """ A tabular portlet widget that performs a simple folder listing.

    Information is fetched from the folder's objects of a given meta-type.
    There's no batching or sorting.

    >>> FolderContentsWidget('the_id')
    <FolderContentsWidget at the_id>
    """

    meta_type = 'Folder Contents Widget'
    _properties = TabularWidget._properties + (
        {'id': 'listed_meta_types', 'type': 'lines', 'mode': 'w',
         'label': 'Meta types to list', 'is_required' : 1},
        {'id': 'cookie_id', 'type': 'string', 'mode': 'w',
         'label': 'Name of cookie for filter params (no cookie if empty)', },
        {'id': 'filter_button', 'type': 'string', 'mode': 'w',
         'label': 'Name of the button used to trigger filtering', },
        )

    listed_meta_types = (
       'CPS Proxy Document',
       'CPS Proxy Folder',
       'CPS Proxy Folderish Document',
       )

    cookie_id = ''

    filter_button = ''

    filter_prefix = 'f_'

    render_method = 'widget_tabular_render'

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

    def passFilters(self, item, filters):
        """True if filters is a subdict of item.
        TODO check if there is something in the dict api for this

        >>> widg = FolderContentsWidget('')
        >>> widg.passFilters({'ab':1, 'cd':2}, {})
        True
        >>> widg.passFilters({'ab':1, 'cd':2}, {'ab': 1})
        True
        >>> widg.passFilters({'ab':1, 'cd':2}, {'ab': 2})
        False
        >>> widg.passFilters({'ab':1, 'cd':2, 'spam': 'a'}, {'ab': 1, 'spam':'a'})
        True
        >>> widg.passFilters({'ab':1, 'cd':2, 'spam': 'a'}, {'ab': 1, 'spam':'b'})
        False
        """

        LOG('passFilters:item', DEBUG, item)
        LOG('passFilters:ilters', DEBUG, filters)
        if not filters:
            return True
        for key, value in filters.items():
            if item.get(key, _missed) != value:
                return False
        else:
            return True

    def listRowDataStructures(self, datastructure, layout, filters=None, **kw):
        """Return an iterator for folder contents datastructures

        We cannot avoid finally fetching all objects, but we try to
        avoid fetching all of them at once.

        Implememtation has become rotten and in need of serious refactoring
        """
        folder = kw.get('context_obj') # typical of portlets
        if folder is None:
            folder = datastructure.getDataModel().getProxy()

        if not _checkPermission(ListFolderContents, folder):
            raise Unauthorized("You are not allowed to list this folder")
        meta_types = datastructure.get('meta_types') or self.listed_meta_types

        if filters is None:
            raise ValueError('Filters is None')

        (b_page, b_start, b_size) = self.getBatchParams(datastructure,
                                                        filters=filters)

        sort_key = filters.pop('sort-on', None)
        sort_order = filters.pop('sort-order', None)
        sort_col = filters.pop('sort-col', None)
        ### XXX the filtering algorithm is dead wrong
        if sort_key is None:
          o_ids = folder.objectIds(meta_types)
        else:
          o_items = folder.objectItems(meta_types)
          # Check Dublin core case
          first = o_items and o_items[0][1].getContent()
          if o_items and callable(getattr(first, sort_key)):
              weighted_items = [(getattr(item.getContent(), sort_key)(), oid)
                                for oid, item in o_items]
          else:
              weighted_items = [(getattr(item.getContent(), sort_key), oid)
                                for oid, item in o_items]

          weighted_items.sort()
          o_ids = [w_item[1] for w_item in weighted_items]
          if sort_order == 'reverse':
              o_ids.reverse()

        nb_pages = self.getNbPages(len(o_ids), b_size)
        batched_ids = o_ids[b_start:b_start+b_size]
        iterprox = (folder[p_id] for p_id in batched_ids)
        iterprox = (proxy for proxy in iterprox
                    if _checkPermission(View, proxy))
        iterdocs = ( (proxy.getContent(), proxy) for proxy in iterprox)
        iterdms = (doc.getTypeInfo().getDataModel(doc,
                                                  proxy=proxy, context=folder)
                   for doc, proxy in iterdocs)
        iterds = (self.prepareRowDataStructure(layout,
                                               DataStructure(datamodel=dm))
                  for dm in iterdms)
        return ((ds for ds in iterds if self.passFilters(ds, filters)),
                b_page, nb_pages)

InitializeClass(FolderContentsWidget)

widgetRegistry.register(FolderContentsWidget)
