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


""" Portlet Widgets. """

import logging
from urllib import quote

from Globals import InitializeClass

from Products.CMFCore.utils import getToolByName

from Products.CPSSchemas.Widget import CPSWidget
from Products.CPSSchemas.Widget import widgetname
from Products.CPSSchemas.DataStructure import DataStructure
from Products.CPSDocument.FlexibleTypeInformation import FlexibleTypeInformation
from Products.CPSPortlets.CPSPortletWidget import CPSPortletWidget
from Products.CPSDashboards.utils import serializeForCookie
from Products.CPSDashboards.utils import unserializeFromCookie
from Products.CPSDashboards.widgets.filter_widgets import CPSIntFilterWidget

from Products.CPSDocument.interfaces import ICPSDocument

logger = logging.getLogger('CPSDashboards.tabular')

SCOPE_SUFFIX = '_scope' # see explanations in filter_widgets

_missed = object()


class TabularWidget(CPSIntFilterWidget):
    """ A generic portlet widget to display tabular contents.

    Uses a layout to render the rows. This layout is fetched from the portlet.
    Subclasses have to override the 'listRowDataModels' method.

    The (optional) render method will get those keyword args:
    - mode: the widget's rendering mode
    - rows: list of rendered rows
    - columns: the common list of widget objects that were used to render
               rows.

    We assume that the 'layout' part of the row layout definition is
    actually a column, because that's what flexible widgets manipulation
    methods are comfortable with. It's up to the layout's render method to
    render this column as a row. To get rid of this assumption, subclasses
    can override the extractColumns method.

    >>> wi = TabularWidget('spam')

    The widget inherits from CPSIntFilterWidget to read batching info from
    request (and cookies) in the prepare phase.
    """

    _properties = _properties = CPSPortletWidget._properties + (
        {'id': 'row_layout', 'type': 'string', 'mode': 'w',
         'label': 'Layout to use for the rows', 'is_required' : 1},
        {'id': 'empty_message', 'type': 'string', 'mode': 'w',
         'label': 'Message to display if listing is empty',},
        {'id': 'is_empty_message_i18n', 'type': 'boolean', 'mode': 'w',
         'label': 'Is the message of emptiness to be translated?'},
        {'id': 'actions_category', 'type': 'string', 'mode': 'w',
         'label': 'Actions category for buttons'},
        {'id': 'cookie_id', 'type': 'string', 'mode': 'w',
         'label': 'Name of cookie for filter params (no cookie if empty)', },
        {'id': 'filter_button', 'type': 'string', 'mode': 'w',
         'label': 'Name of the button used to trigger filtering', },
        {'id': 'filter_prefix', 'type': 'string', 'mode': 'w',
         'label': 'Prefix of filtering widgets', },
        {'id': 'items_per_page', 'type': 'int', 'mode': 'w',
         'label': 'Maximum number of results per page', },
        {'id': 'filter_items_per_page', 'type': 'string', 'mode': 'w',
         'label': 'Filter used for number of results per page', },
        {'id': 'batching_gadget_pages', 'type': 'int', 'mode': 'w',
         'label': 'Number of context pages displayed in batching gadget'},
        )

    row_layout = ''
    render_method = ''
    empty_message = ''
    is_empty_message_i18n = False
    actions_category = ''
    actions = ()
    cookie_id = ''
    filter_button = ''
    filter_prefix = 'q_'
    items_per_page = 10
    batching_gadget_pages = 3
    filter_items_per_page = ''

    def prepareRowDataStructure(self, layout, datastructure):
        """Have layout prepare row datastructure and return it."""
        layout.prepareLayoutWidgets(datastructure)
        return datastructure

    def listRowDataStructures(self, datastructure, layout, **kw):
        """Return items datastructures, prepared by layout

        It's probably a good idea to return an iterator.
        """
        raise NotImplementedError

    def getCallingObject(self, datastructure):
        """Get the object for which this widget is called.

        Typically a portlet."""

        dm = datastructure.getDataModel()
        proxy = dm.getProxy()
        if proxy is None:
            return dm.getObject()
        else:
            return proxy

    def getMethodContext(self, datastructure):
        """Return the context from where to lookup the layout rendering method.

        Override this if you want to replace a slow zpt parsing by fixed python
        code.

        To do this for widgets would require to pass the context at
        datamodel init time or hack it afterwards.
        This could be dangerous because of ACL checks and local roles.
        """

        return datastructure.getDataModel().getContext()

    def setCookieFromMapping(self, request, mapping, path_method=False):
        """Set a dict in cookie."""

        if path_method:
            path = request['URLPATH0']
        else:
            path = request['URLPATH1']

        cookie = serializeForCookie(mapping, charset=self.default_charset)
        logger.debug("Setting cookie, path=%s" % path)
        request.RESPONSE.setCookie(self.cookie_id, cookie, path=path)

    def buildFilters(self, datastructure, cookie_path_method=False):
        """Build query according to datastructure, query and cookies.

        Cookies not implemented.
        Assumptions: the post is made with widgets whose ids start all with
        self.filter_prefix
        and correspond to other widget ids present in items.
        cookie_path_method: boolean to tweak the path to set cookie.
          if true, the full requested path is used
          The default behavior is usefull to share between different views of
          the same object (e.g., cpsdocument_edit_form and cpsdocument_view)
        """

        # extract filters from datastructure
        prefix = self.filter_prefix
        prefilt = dict( (key, item)
                       for key, item in datastructure.items()
                       if key.startswith(prefix) )

        # if filtering uses a post, set cookie
        request = self.REQUEST
        if self.cookie_id and request.form.get(self.filter_button):
            self.setCookieFromMapping(request, prefilt,
                                      path_method=cookie_path_method)

        # replace some empty filters by the corresponding total scope
        # and remove the others
        filters = {}
        pref_len = len(prefix)
        for key, item in prefilt.items():
            if item and not key.endswith(SCOPE_SUFFIX):
                filters[key[pref_len:]] = item
                continue
            scope = datastructure.get(key + SCOPE_SUFFIX)
            if scope is not None:
                filters[key[pref_len:]] = scope

        # path and rpath. Meant to reproduce what CPSDefault's search.py does
        rpaths = filters.pop('folder_prefix', None)
        if not 'path' in filters:
            if rpaths is not None:
                utool = getToolByName(self, 'portal_url')
                base = '/'.join(utool.getPortalObject().getPhysicalPath())
                if isinstance(rpaths, list):
                    filters['path'] = ['%s/%s' % (base, rpath)
                                       for rpath in rpaths]
                elif isinstance(rpaths, str):
                    filters['path'] = '%s/%s' % (base, rpaths)

        logger.debug(' filters: %s' %filters)
        return filters

    def getBatchParams(self, datastructure, filters=None):
        """Extract batching parameters from given dict."""

        b_page = datastructure.get(self.getWidgetId())
        if b_page is None:
            b_page = 1
        else:
            b_page = int(b_page)

        items_per_page = self.items_per_page
        if filters is not None and self.filter_items_per_page:
            items_per_page = int(filters.pop(self.filter_items_per_page,
                                             self.items_per_page))
        else:
            items_per_page = self.items_per_page

        b_start = (b_page-1)*items_per_page
        return (b_page, b_start, items_per_page)

    def getNbPages(self, nb_items, items_per_page=None):
        """Return number of pages that nb_items items make."""

        if nb_items:
            if items_per_page is None:
                items_per_page = self.items_per_page
            return (nb_items-1)/items_per_page+1
        else:
            return 0

    def columnFromWidget(self, widget, datastructure,
                         sort_filter='sort'):
        """ make column info from a widget object.

        Return (widget, boolean, token, get_req) where:
        - boolean tells whether this column is used as sorting reference
        - token is the associated token (e.g, 'ascending' etc)
        - get_req is the get part of the url to toggle sort.
        XXX might break with flexible layouts because it relies on the column
        id.
        XXX might be a good idea to make a property out of 'sort_widget'
        XXX this currently uses -col,-token and -on suffixes to exchange info
        with
        a toggable widget of the current object (we have a corresponding
        datastructure but cannot have this widget in itself).
        Make these strings default values of props on the tabular
        widget (an sort widget also) for flexibility and and tight default
        config
        """

        sortable = getattr(widget, 'sortable', None)
        if not sortable:
            return (widget, False, '', '')

        # prepare the get request
        wid = widget.getWidgetId()
        sort_wid = self.filter_prefix + sort_filter
        sort_name = widgetname(sort_wid)
        get_req = '?%s=%s&%s-col=%s' % (sort_name,
                                        quote(sortable),
                                        sort_name,
                                        wid,
                                        )
        filt_butt = getattr(self, 'filter_button', '')
        if filt_butt:
            get_req += '&%s=go' % filt_butt

        sort_col = datastructure.get(sort_wid+'-col') # make -col a prop
        if sort_col != wid:
            return (widget, False, '', get_req)

        # this column is the sorting reference.
        token = datastructure.get(sort_wid+'-order') # make -order a prop
        return (widget, True, token, get_req)

    def extractColumns(self, datastructure, layout_structure):
        """ Extract column info for render method from a layout structure. """

        return [ self.columnFromWidget(row[0]['widget'], datastructure)
                 for row in layout_structure['rows'] ]

    def getActions(self, datastructure):
        if not self.actions_category:
            return None

        atool = getToolByName(self, 'portal_actions')

        proxy = datastructure.get('context_obj') # if from portlet
        if proxy is None:
            proxy = datastructure.getDataModel().getProxy()

        if proxy is None:
            return []

        cat = self.actions_category or 'object'
        all_actions = atool.listFilteredActionsFor(proxy)
        actions = all_actions.get(self.actions_category, ())
        return [{'title': action['name'],
                'url': action['url'],
                 'id' : action['id'],}
                for action in actions]

    def getModeFromLayoutMode(self, layout_mode, datamodel):
        """ Allow some fine tweakings about forms. """

        if layout_mode == 'search_results':
            return 'search'
        else:
            return CPSWidget.getModeFromLayoutMode(self, layout_mode, datamodel)

    def getBatchingInfo(self, current_page, nb_pages):
        """ Return a dict to be used by render_method."""

        first_page = max(current_page - self.batching_gadget_pages, 1)
        last_page = min(current_page + self.batching_gadget_pages,
                        nb_pages)
        return {'current_page': current_page,
                'nb_pages': nb_pages,
                'linked_pages' : range(first_page, last_page+1),
                'form_key' : self.getHtmlWidgetId(),
                # search views need to know they are displaying results:
                'filter_button': self.filter_button}



    def render(self, mode, datastructure, **kw):
        """ Render datastructure according to mode.

        Rows layout structures are computed once and for all, on the first
        object to display.
        """

        # global preparations
        calling_obj = self.getCallingObject(datastructure)
        
        if calling_obj is None: # happens on creation
            return ''

        # GR tired of this duplication. refactor
        proxy = datastructure.get('context_obj') # if from portlet
        if proxy is None:
            proxy = datastructure.getDataModel().getProxy()

        ## lookup of row layout
        #  calling_obj is typically: a proxy, a CPSDocument/Portlet, a mappping
        #  (cf LayoutsTool.renderLayout)
        lid = self.row_layout
        if ICPSDocument.providedBy(calling_obj):
            fti = calling_obj.getTypeInfo()
            # get the layout from object because it might be flexible
            row_layout = fti.getLayout(lid, calling_obj)
        else:
            ltool = getToolByName(self, 'portal_layouts')
            row_layout = getattr(ltool, lid)
            fti = FlexibleTypeInformation('transient')

        # build filters and maybe set cookie
        filters = self.buildFilters(datastructure,
                                    cookie_path_method=mode=='search')

        # fetch prepared row datastructures
        row_dss, current_page, nb_pages = self.listRowDataStructures(
            datastructure, row_layout, filters=filters, **kw)

        layout_structures = None

        # rows rendering
        rendered_rows = []
        meth_context = self.getMethodContext(datastructure)
        for row_ds in row_dss:
            # compute layout_structures if needed
            if layout_structures is None:
                row_dm = row_ds.getDataModel()
                layout_structures = [
                    row_layout.computeLayoutStructure('view', row_dm)]

            # render from row_ds
            rendered = fti._renderLayouts(layout_structures,
                                          row_ds,
                                          context=meth_context,
                                          layout_mode='view',
                                          )
            rendered_rows.append(rendered)

        if not self.render_method: # default behaviour that can still be useful
            return '\n'.join(rendered_rows)

        meth = getattr(meth_context, self.render_method, None)
        if meth is None:
            raise RuntimeError("Unknown Render Method %s for widget type %s"
                               % (self.render_method, self.getId()))

        if layout_structures:
            layout_structure = layout_structures[0] # only one layout
            columns = self.extractColumns(datastructure, layout_structure)
        else:
            columns = ()
        actions = self.getActions(datastructure)

        # finding here_url to feed to render method
        here = proxy or datastructure.getDataModel().getContext()
        here_url = here.absolute_url()

        # in search mode, we must add the view name to here_url
        # PUBLISHED would be the view class instance or the skin zpt or py
        if mode == 'search':
            request = self.REQUEST
            if request is not None:
                # Better use __name__ for Five views.
                view_name = self.REQUEST['URLPATH0'].split('/')[-1]
                here_url += '/' + view_name

        if nb_pages <= 1:
            batching_info = None
        else:
            batching_info = self.getBatchingInfo(current_page, nb_pages)

        return meth(mode=mode, columns=columns,
                    rows=rendered_rows, actions=actions,
                    here_url=here_url, batching_info=batching_info,
                    base_url=getToolByName(self, 'portal_url').getBaseUrl(),
                    empty_message=self.empty_message)
