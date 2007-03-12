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


""" Catalog Tabular Widgets. """

import logging

from Globals import InitializeClass
from AccessControl import Unauthorized
from AccessControl import getSecurityManager
from ZODB.loglevels import TRACE as TRACE

from Products.CMFCore.utils import _checkPermission, getToolByName
from Products.CMFCore.permissions import View, ListFolderContents

from Products.CPSSchemas.Widget import CPSWidget
from Products.CPSSchemas.Widget import widgetRegistry
from Products.CPSSchemas.DataModel import DataModel
from Products.CPSSchemas.DataStructure import DataStructure
from Products.CPSSchemas.BasicWidgets import renderHtmlTag

from Products.CPSDashboards.braindatamodel import BrainDataModel
from Products.CPSDashboards.widgets.tabular import TabularWidget

logger = logging.getLogger('CPSDashboards.widgets.catalog')

class CatalogTabularWidget(TabularWidget):
    """ A tabular portlet widget that performs a catalog query.

    Uses the inherited reading of filter params from datastructure and
    does further work to build the query out of them in the filterToQuery
    method.

    >>> CatalogTabularWidget('the id')
    <CatalogTabularWidget at the_id>
    """

    meta_type = 'Catalog Tabular Widget'

    render_method = 'widget_tabular_render'

    _properties = TabularWidget._properties + (
        {'id': 'fulltext_keys', 'type': 'tokens', 'mode': 'w',
         'label': 'Catalog keys for fulltext searchs'},
        {'id': 'fulltext_ors', 'type': 'tokens', 'mode': 'w',
         'label': 'Input filters used for fulltext ORs',},
        {'id': 'users_groups_filters', 'type': 'tokens', 'mode': 'w',
         'label': "Input filters to replace by user and user's group",},
        {'id': 'range_min_suffix', 'type': 'string', 'mode': 'w',
         'label': "Suffix for widget ids that encode a min range bound",},
        {'id': 'range_max_suffix', 'type': 'string', 'mode': 'w',
         'label': "Suffix for widget ids that encode a max range bound",},
        )

    # support for more than one full text index.
    # the two props should be fully synchronized
    fulltext_keys = ('SearchableText', 'ZCTitle')
    fulltext_ors = ('ZCText_or', 'ZCTitle_or')
    users_groups_filters = ()
    range_min_suffix = "_min"
    range_max_suffix = "_max"

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

    def filtersToQuery(self, filters):
        """Updates dict to build a query from filters.

        Takes care of fulltext issues, range queries and access rights.
        """

        for fulltext_or, fulltext_key in zip(self.fulltext_ors,
                                             self.fulltext_keys):
            filter_or = filters.pop(fulltext_or, '').strip()
            tokens = [token.strip() for token in filter_or.split()]
            nb_tok = len(tokens)

            if nb_tok == 1:
                query_or = tokens[0]
            else:
                query_or = '(%s)' % ' OR '.join(tokens)

            if nb_tok:
                filters[fulltext_key] = query_or

        #Ranges
        to_del = set()
        for key in filters.keys():
            if key in to_del:
                # in case of min:max, do not build the quesry twice
                continue
            if key.endswith(self.range_min_suffix):
                key_base = key[:-len(self.range_min_suffix)]
            elif key.endswith(self.range_max_suffix):
                key_base = key[:-len(self.range_max_suffix)]
            else:
                # this is a not a range param: no query to build
                continue
            # computing the range (min, max or min:max)
            key_min = key_base + self.range_min_suffix
            if filters.has_key(key_min):
                to_del.add(key_min)
            value_min = filters.get(key_min)
            key_max = key_base + self.range_max_suffix
            if filters.has_key(key_max):
                to_del.add(key_max)
            value_max = filters.get(key_max)

            # building the query from the non empty values
            if value_min is not None and value_max is not None:
                filters[key_base] = {'query': [value_min, value_max],
                                     'range' : "min:max"}
            elif value_min is not None:
                filters[key_base] = {'query': value_min,
                                     'range' : "min"}
            elif value_max is not None:
                filters[key_base] = {'query': value_max,
                                     'range' : "max"}

        for key in to_del:
            del filters[key]

        #Filters to feed with user id and its groups
        if self.users_groups_filters:
            aclu = getToolByName(self, 'acl_users')
            user = getSecurityManager().getUser()
            allowed = aclu.getAllowedRolesAndUsersOfUser(user)

            for filt in self.users_groups_filters:
                if filters.get(filt):
                    filters[filt] = allowed

        # Path
        path = filters.get('path')
        if path is None or filters.get('path_physical', False):
            return

        utool = getToolByName(self, 'portal_url')
        portal_path = '/' + utool.getPhysicalPath()[1]
        if not path:
            path = portal_path
        elif path[0] == '/':
            path = portal_path + path
        else:
            path = '%s/%s' % (portal_path, path)
        filters['path'] = path

    def _doBatchedQuery(self, catalog, b_start, b_size, query):
        """ Return batched results, total number of results.

        query will be changed to what was actually sent to the catalog."""

        brains = catalog(**query)
        return brains[b_start:b_start+b_size], len(brains)

    def listRowDataStructures(self, datastructure, layout, filters=None, **kw):
        """Return datastructures holding search results meta-data & batch info.
        """

        catalog = getToolByName(self, 'portal_catalog')

        if filters is None:
            raise ValueError('Filters is None')

        query = filters
        self.filtersToQuery(query)
        (b_page, b_start, b_size) = self.getBatchParams(datastructure, filters=filters)

        logger.log(TRACE, query)
        brains, nb_results = self._doBatchedQuery(catalog,
                                                  b_start, b_size, query)

        nb_pages = self.getNbPages(nb_results, items_per_page=b_size)
        logger.debug("CatalogTabularWidget: "
                     "%d results, %d pages (current %d)" % (nb_results,
                                                            nb_pages,
                                                            b_page))

        dms = (BrainDataModel(brain) for brain in brains)
        datastructures = (DataStructure(datamodel=dm) for dm in dms)
        return ([self.prepareRowDataStructure(layout, ds)
                 for ds in datastructures], b_page, nb_pages)

InitializeClass(CatalogTabularWidget)

widgetRegistry.register(CatalogTabularWidget)


class LuceneTabularWidget(CatalogTabularWidget):

    meta_type = 'Lucene Tabular Widget'

    def _doBatchedQuery(self, catalog, b_start, b_size, query):
        """ Return batched results, total number of results.

        query will be changed to what wbas actually sent to the catalog."""

        query['b_start'] = b_start
        query['b_size'] = b_size

#        logger.debug('Final query: %s', query)
        brains = catalog(**query)
        if brains:
            return brains, brains[0].out_of
        else:
            return [], 0

InitializeClass(LuceneTabularWidget)

widgetRegistry.register(LuceneTabularWidget)
