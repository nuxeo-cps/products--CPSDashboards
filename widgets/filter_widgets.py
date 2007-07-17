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

"""Widget definitions for CPSDashboards query parameters and cookie management"""

import logging

from Globals import InitializeClass

from Products.CMFCore.utils import getToolByName
from Products.CPSSchemas.Widget import CPSWidget
from Products.CPSSchemas.DataStructure import DataStructure
from Products.CPSSchemas.Widget import widgetRegistry
from Products.CPSSchemas.BasicWidgets import (CPSSelectWidget,
                                              CPSMultiSelectWidget,
                                              CPSBooleanWidget,
                                              CPSStringWidget,
                                              CPSIntWidget)
from Products.CPSSchemas.SearchWidgets import CPSSearchLocationWidget
from Products.CPSSchemas.ExtendedWidgets import (CPSDateTimeWidget,
                                                 CPSGenericSelectWidget)
from Products.CPSDashboards.utils import unserializeFromCookie

from Products.CPSSchemas.Widget import widgetname

logger = logging.getLogger('CPSDashboards.widgets.filter_widgets')

DS_COOKIES = '_cookies'

class FakeRequest:
    def __init__(self, **kw):
        self.form = kw

class FilterWidgetMixin:
    """General Mixin for all FilterWidgets.

    - prepare datastructure from dm, request and cookie.
    - wear info about boolean operators (condition)
    """

    _properties = (
        {'id': 'cookie_id', 'type': 'string', 'mode': 'w',
         'label': 'Name of cookie for filter params (no cookie if empty)', },
        {'id': 'insertion_boolean_op', 'type': 'selection', 'mode': 'w',
         'select_variable': 'boolean_ops',
         'label': 'Boolean operator in which to insert this filter', },
#        {'id': 'internal_boolean_op', 'type': 'selection', 'mode': 'w',
#         'select_variable': 'boolean_ops',
#         'label': 'Boolean operator to apply inside this filter', },
        )

    boolean_ops = ('', 'OR', 'NOT', 'AND')
    insertion_boolean_op = ''
    cookie_id = ''

    def readCookie(self, datastructure, wid):
        """Read a value for datastructure from cookie.

        keep unserialized cookies dicts on datastructure.
        Was preferred over calling updateFromMapping to avoid overriding
        already performed full preparations by non cookie-aware widgets.

        XXX This shouldn't be done by widgets, see #1606

        """
        if not self.cookie_id:
            return

        ds_cookies = getattr(datastructure, DS_COOKIES, None)
        if ds_cookies is None:
            ds_cookies = {}
            setattr(datastructure, DS_COOKIES, ds_cookies)

        cookie = ds_cookies.get(self.cookie_id)
        if cookie is None:
            cookie = self.REQUEST.cookies.get(self.cookie_id)
            if cookie is None:
                return

            # we have to convert from unicode. There should be only identifiers
            # so we don't catch UnicodeEncodeErrors
            cookie = unserializeFromCookie(string=cookie,
                                           charset=self.default_charset)
            logger.debug('Widget %s, read cookie:%s', wid, cookie)
            ds_cookies[self.cookie_id] = cookie

        try:
            read = cookie.get(wid)
        except AttributeError: # not a dict
            return

        portal = getToolByName(self, 'portal_url').getPortalObject()
        charset = portal.default_charset
        
        if isinstance(read, unicode) and charset != "unicode":  # minjson makes all strings unicode
            read = read.encode('iso-8859.15')

        return read

    def _expireCookie(self):
        """Expire cookie inconditionnaly."""

        request = self.REQUEST
        path = request['URLPATH1']
        request.RESPONSE.expireCookie(self.cookie_id, path=path)

    def expireCookie(self, **kw):
        """Expire cookie if appropriate."""

        if self.cookie_id and kw.get('layout_mode') == 'edit':
            self._expireCookie()

    def prepare(self, datastructure, call_base=True, **kw):
        """ prepare datastructure from datamodel, request and cookie.

        cookie not implemented.

        >>> datastructure = {}
        >>> widget = CPSSelectFilterWidget('the_id')
        >>> widget.REQUEST = FakeRequest(widget__the_id='abc')
        XXX test needs to be finished
        """

        wid = self.getWidgetId()

        # from datamodel: call base class if required
        if call_base:
            klass = getattr(self, 'base_widget_class')
            klass.prepare(self, datastructure, **kw)

        # from cookie
        from_cookie = self.readCookie(datastructure, wid)
        if from_cookie is not None:
            datastructure[wid] = from_cookie

        # from request form
        posted = self.REQUEST.form.get(widgetname(wid))
        if posted is not None:
            datastructure[wid] = posted

    def validate(self, ds, **kw):
        klass = getattr(self, 'base_widget_class', None)
        if klass is not None and not klass.validate(self, ds, **kw):
            return False

        self.expireCookie(**kw)
        return True


#
# Widgets
#

class CPSSelectFilterWidget(FilterWidgetMixin, CPSSelectWidget):
    """A select widget that prepares from request and cookies.

    Problem fixed by ugly hack: catalog would want a singleton instead of
    a string and multiselect inappropriate.
    """

    meta_type = 'Select Filter Widget'
    base_widget_class = CPSSelectWidget

    _properties = (CPSSelectWidget._properties
                   + FilterWidgetMixin._properties
                   + ({'id': 'defines_scope', 'type': 'boolean', 'mode': 'w',
                       'label': "Is the union of all values is more restrictive than no filtering?"},
                      {'id': 'reject_from_scope', 'type': 'tokens', 'mode': 'w',
                       'label': "Items from voc to exclude from scope"},
                      {'id': 'total_scope', 'type': 'tokens', 'mode': 'w',
                       'label': "Fixed total scope (takes precedence)"})
                   )

    defines_scope = False
    reject_from_scope = ()
    total_scope = ()

    def getScope(self, datastructure):
        """return a total scope that might not be equivalent for query
        engines than dropping the value.

        Use-case for this oddity:
        voc of locally accepted portal_types.
        '' Is used at position 0 to mean 'all',
        but the query maker will use the list of all existing portal_types
        and datastructure cannot hold lists, because of type inconsistency.

        #XXX TODO factorize in mixin class
        """

        if self.total_scope:
            return self.total_scope

        items = self._getVocabulary(datastructure).keys()
        if not items[0]: # raise on empty voc (good thing)
            if self.reject_from_scope:
                return list(it for it in items[1:]
                            if not it in self.reject_from_scope)
            else:
                return list(items[1:]) # see use-case in docstring
        else:
            return list(items)


    def prepare(self, ds, **kw):
        """Prepare datastructure from datamodel."""
        CPSSelectWidget.prepare(self, ds, **kw)
        FilterWidgetMixin.prepare(self, ds, call_base=False, **kw)
        wid = self.getWidgetId()
        if self.defines_scope and not ds[wid]:
            ds[wid+'_scope'] = self.getScope(ds)

InitializeClass(CPSSelectFilterWidget)

widgetRegistry.register(CPSSelectFilterWidget)

class CPSGenericSelectFilterWidget(FilterWidgetMixin, CPSGenericSelectWidget):
    """A select widget that prepares from request and cookies.

    Problem fixed by ugly hack: catalog would want a singleton instead of
    a string and multiselect inappropriate.
    """

    meta_type = 'Generic Select Filter Widget'
    base_widget_class = CPSGenericSelectWidget

    _properties = (CPSGenericSelectWidget._properties
                   + FilterWidgetMixin._properties
                   + ({'id': 'defines_scope', 'type': 'boolean', 'mode': 'w',
                       'label': "Is the union of all values is more restrictive than no filtering?"},
                      {'id': 'reject_from_scope', 'type': 'tokens', 'mode': 'w',
                       'label': "Items from voc to exclude from scope"},
                      {'id': 'total_scope', 'type': 'tokens', 'mode': 'w',
                       'label': "Fixed total scope (takes precedence)"})
                   )

    defines_scope = False
    reject_from_scope = ()
    total_scope = ()

    def getScope(self, datastructure):
        """return a total scope that might not be equivalent for query
        engines than dropping the value.

        Use-case for this oddity:
        voc of locally accepted portal_types.
        '' Is used at position 0 to mean 'all',
        but the query maker will use the list of all existing portal_types
        and datastructure cannot hold lists, because of type inconsistency.

        #XXX TODO factorize in mixin class
        """

        if self.total_scope:
            return self.total_scope

        items = self._getVocabulary(datastructure).keys()
        if not items[0]: # raise on empty voc (good thing)
            if self.reject_from_scope:
                return list(it for it in items[1:]
                            if not it in self.reject_from_scope)
            else:
                return list(items[1:]) # see use-case in docstring
        else:
            return list(items)


    def prepare(self, ds, **kw):
        """Prepare datastructure from datamodel."""
        CPSGenericSelectWidget.prepare(self, ds, **kw)
        FilterWidgetMixin.prepare(self, ds, call_base=False, **kw)
        wid = self.getWidgetId()
        if self.defines_scope and not ds[wid]:
            ds[wid+'_scope'] = self.getScope(ds)

InitializeClass(CPSGenericSelectFilterWidget)

widgetRegistry.register(CPSGenericSelectFilterWidget)


class CPSMultiSelectFilterWidget(FilterWidgetMixin, CPSMultiSelectWidget):
    """A multiselect widget that prepares from request and cookies. """

    meta_type = 'MultiSelect Filter Widget'
    _properties = CPSMultiSelectWidget._properties + FilterWidgetMixin._properties
    base_widget_class = CPSMultiSelectWidget

InitializeClass(CPSMultiSelectFilterWidget)

widgetRegistry.register(CPSMultiSelectFilterWidget)


class CPSStringFilterWidget(FilterWidgetMixin, CPSStringWidget):
    """A string widget that prepares from request and cookies. """

    meta_type = 'String Filter Widget'
    _properties = CPSStringWidget._properties + FilterWidgetMixin._properties
    base_widget_class = CPSStringWidget

InitializeClass(CPSStringFilterWidget)

widgetRegistry.register(CPSStringFilterWidget)

class CPSBooleanFilterWidget(FilterWidgetMixin, CPSBooleanWidget):
    """The filter widget counterpart to Search Location Widget.

    Would become useless if #1606 is ever taken care of.
    """

    meta_type = 'Boolean Filter Widget'
    _properties = CPSBooleanWidget._properties + FilterWidgetMixin._properties
    base_widget_class = CPSBooleanWidget

InitializeClass(CPSBooleanFilterWidget)
widgetRegistry.register(CPSBooleanFilterWidget)
    
class CPSFixedFilterWidget(CPSStringWidget):
    """A string widget that puts a fixed value in datastructure.

    Used to transmit search criteria that don't depend on user input.
    """

    meta_type = 'Fixed Filter Widget'
    _properties = CPSStringWidget._properties + (
        {'id': 'value', 'type': 'string', 'mode': 'w', 'label': 'Fixed value'},)

    value = ''

    def prepare(self, ds):
        ds[self.getWidgetId()] = self.value

InitializeClass(CPSFixedFilterWidget)

widgetRegistry.register(CPSFixedFilterWidget)


class CPSFixedListFilterWidget(CPSStringWidget):
    """A string widget that puts a fixed list of string values in datastructure.

    Used to transmit search criteria that don't depend on user input.
    """

    meta_type = 'Fixed List Filter Widget'
    _properties = CPSStringWidget._properties + (
        {'id': 'values', 'type': 'lines', 'mode': 'w', 'label': 'Fixed values'},)

    values = ()

    def prepare(self, ds):
        ds[self.getWidgetId()] = self.values

InitializeClass(CPSFixedListFilterWidget)

widgetRegistry.register(CPSFixedListFilterWidget)


TOKEN_SUFFIX = '_token'

class CPSToggableCriterionWidget(FilterWidgetMixin, CPSSelectWidget):
    """A widget that manipulates a decorated criterion.

    typical use-case: key to sort on and sort direction. In this use-case, one
    might use the <wid><ref_suffix> to indicate the name of the column (might
    differ from the sort-on key.
    """

    meta_type = 'Toggable Criterion Widget'

    _properties = CPSSelectWidget._properties +\
                  FilterWidgetMixin._properties + (
        {'id': 'filter_button', 'type': 'string', 'mode': 'w',
         'label': 'Name of the button used to trigger filtering', },
        {'id': 'toggle_tokens', 'type': 'tokens', 'mode': 'w',
         'label': 'Tokens to toggle'}, # we could use a vocabulary, too
        {'id': 'criterion_suffix', 'type': 'string', 'mode': 'w',
         'label': 'Suffix for the criterion'},
        {'id': 'token_suffix', 'type': 'string', 'mode': 'w',
         'label': 'Suffix for the token'},
        {'id': 'ref_suffix', 'type': 'string', 'mode': 'w',
         'label': 'Suffix for a further associated reference'},
        )

    # default values for catalog sort use-case
    toggle_tokens = ('', 'reversed')
    criterion_suffix = '-on'
    token_suffix = '-order'
    ref_suffix = '-col'
    filter_button = ''

    def validate(self, ds, **kw):
        self.expireCookie(**kw)

        # ugly hack to let CPSSelectWidget do the job
        wid = self.getWidgetId()
        crit_key = wid + self.criterion_suffix
        ds[wid] = ds[crit_key]

        res = CPSSelectWidget.validate(self, ds, **kw)

        if wid != crit_key:
            del ds[wid]
        return res

    def prepare(self, ds, **kw):
        """prepare datastructure from datamodel, request and cookie. """

        wid = self.getWidgetId()
        crit_key = wid + self.criterion_suffix
        token_key = wid + self.token_suffix
        ref_key = wid + self.ref_suffix

        keys = (crit_key, token_key, ref_key)

        dm = ds.getDataModel()

        # reading from datamodel if apppropriate
        for key, field in zip(keys, self.fields):
            ds[key] = dm[field]

        # from cookie
        for key in keys:
            from_cookie = self.readCookie(ds, key)
            if from_cookie is not None:
               ds[key] = from_cookie

        # from request form: criterion
        form =  self.REQUEST.form
        posted = form.get(widgetname(wid))

        # do toggle token
        # if not post-filtering *from* the results page, start over
        logger.debug('Toggable Widget posted: %s', posted)
        if posted is not None:
            button = self.filter_button
            # check button non void for partial BBB
            if posted != ds.get(crit_key) or (button and button not in form):
                ds[crit_key] = posted
                ds[token_key] = self.toggle_tokens[0]
            else:
                i = list(self.toggle_tokens).index(ds[token_key])
                order = len(self.toggle_tokens)
                ds[token_key] = self.toggle_tokens[(i+1) % order]

        # from request: ref
        posted = self.REQUEST.form.get(widgetname(ref_key))
        if posted is not None:
            ds[ref_key] = posted
        else:
            ds.pop(ref_key, None)
        logger.debug('ref: %s', ds.get(ref_key))
        logger.debug('crit: %s', ds.get(crit_key))
        logger.debug('token: %s', ds.get(token_key))


    def render(self, mode, datastructure, **kw):
        """ render in mode from datastructure.

        Useful for search pages or dashboards edit views."""

        wid = self.getWidgetId()
        crit_key = wid + self.criterion_suffix

        # ugly hack to let CPSSelectWidget do the job
        datastructure[wid] = datastructure[crit_key]
        rendered = CPSSelectWidget.render(self, mode, datastructure, **kw)
        if wid != crit_key:
            del datastructure[wid]
        return rendered

InitializeClass(CPSToggableCriterionWidget)

widgetRegistry.register(CPSToggableCriterionWidget)

class CPSPathWidget(CPSWidget):
    """Put path to context_obj or current proxy, ready to use by catalog."""

    meta_type = 'Path Widget'

    def prepare(self, datastructure, **kw):
        proxy = (kw.get('context_obj', False)
                 or datastructure.getDataModel().getProxy())
        if proxy is None:
            return

        wid = self.getWidgetId()
        datastructure[wid] = '/'.join(proxy.getPhysicalPath())
        # used by filtersToQuery methods
        datastructure[wid + '_physical'] = True

    def validate(self, datastructure, **kw):
        return 1

    def render(self, mode, datastructure, **kw):
        return ''


InitializeClass(CPSPathWidget)

widgetRegistry.register(CPSPathWidget)

class CPSDateTimeFilterWidget(FilterWidgetMixin, CPSDateTimeWidget):
    """ Puts its argument in datastructure.

    This widget would become useless after #1606 is done
    """

    meta_type = 'DateTime Filter Widget'
    _properties = CPSDateTimeWidget._properties + FilterWidgetMixin._properties

    base_widget_class = CPSDateTimeWidget

    def prepare(self, datastructure, **kw):
        wid = self.getWidgetId()
        if self.fields:
            CPSDateTimeWidget.prepare(self, datastructure, **kw)

        # from cookie
        v = self.readCookie(datastructure, wid)
        subkeys = ['%s_%s' % (wid, k) for k in ['date', 'hour', 'minute']]
        subvalues = ((k,self.readCookie(datastructure, k))
                     for k in subkeys)
        subvalues = dict( (k, v ) for k, v in subvalues if v is not None)

        if v is not None:
            try:
                self._prepareDateTimeFromValue(v, datastructure, **kw)
            except ValueError:
                # XXX OG: Ugly, see #1606
                pass

        # from request form
        form = self.REQUEST.form
        posted = self.REQUEST.form.get(widgetname(wid))
        if posted is not None:
            try:
                self._prepareDateTimeFromValue(posted, datastructure, **kw)
            except ValueError:
                # XXX OG: Ugly, see #1606
                pass

        subvalues.update(dict( (k, form[widgetname(k)])
                              for k in subkeys if widgetname(k) in form))

        if subvalues:
            datastructure.updateFromMapping(subvalues)
            # explicitely posted (or cookie) based sub values take precedence
            # and should bt the only present anyway
            cheat_dm = {}
            cheat_ds = DataStructure(data=subvalues, datamodel=cheat_dm)
            if subkeys[1] not in cheat_ds:
                cheat_ds[subkeys[1]] = self.time_hour_default
            if subkeys[2] not in cheat_ds:
                cheat_ds[subkeys[2]] = self.time_minutes_default

            # it's really time for #1606
            CPSDateTimeWidget.validate(self, cheat_ds, **kw)
            datastructure[wid] = cheat_dm[self.fields[0]]

    def _prepareDateTimeFromValue(self, value, datastructure, **kw):
        """Same as CPSDateTimeWidget.prepare but use value instead of dm"""
        # get date time info, mode is not known here
        v, date, hour, minute = self.getDateTimeInfo(value, mode=None)
        wid = self.getWidgetId()
        datastructure[wid] = v
        datastructure[wid + '_date'] = date
        datastructure[wid + '_hour'] = hour or self.time_hour_default
        datastructure[wid + '_minute'] = minute or self.time_minutes_default



InitializeClass(CPSDateTimeFilterWidget)

widgetRegistry.register(CPSDateTimeFilterWidget)

class CPSIntFilterWidget(FilterWidgetMixin, CPSIntWidget):
    """ Puts its argument in datastructure. """

    meta_type = 'Int Filter Widget'
    _properties = CPSIntWidget._properties + FilterWidgetMixin._properties

    def validate(self, datastructure, **kw):
        """ Update datamodel from datastructure """
        #XXX GR ugly hack see #1606
        self.prepare(datastructure)
        value = datastructure.get(self.getWidgetId())
        if isinstance(value, int):
            dm = datastructure.getDataModel()
            dm[self.fields[0]] = value
            return 1
        else:
           return CPSIntWidget.validate(self, datastructure, **kw)

    def prepare(self, datastructure, **kw):
        wid = self.getWidgetId()
        dm = datastructure.getDataModel()
        if self.fields: # Use-case for no fields: batching
           datastructure[wid] = dm[self.fields[0]]

        # from cookie
        from_cookie = self.readCookie(datastructure, wid)
        if from_cookie is not None:
            try:
                datastructure[wid] = int(from_cookie)
            except ValueError:
                # XXX OG: Ugly, see #1606
                pass

        # from request form
        posted = self.REQUEST.form.get(widgetname(wid))
        if posted is not None:
            try:
                datastructure[wid] = int(posted)
            except ValueError:
                # XXX OG: Ugly, see #1606
                pass


InitializeClass(CPSIntFilterWidget)

widgetRegistry.register(CPSIntFilterWidget)

class CPSToDoFilterWidget(CPSSelectFilterWidget):
    """ A widget to translate a list of alternatives in several booleans.

    See doc/developer/filter_widgets for explanation.

    XXX GR: find some better name. Suggestions welcome.
    """

    meta_type = "To Do Filter Widget"

    _properties = CPSSelectFilterWidget._properties + (
        {'id': 'forward_values', 'type': 'tokens', 'mode': 'w',
         'label': 'Values to be forwarded to an index'},
        {'id': 'forward_indexes', 'type': 'tokens', 'mode': 'w',
         'label': 'Filter widget id to forward values to'},
        )

    forward_values = ()
    forward_indexes = ()

    def prepare(self, ds, **kw):
        """Prepare datastructure from datamodel."""
        CPSSelectWidget.prepare(self, ds, **kw)
        FilterWidgetMixin.prepare(self, ds, call_base=False, **kw)
        wid = self.getWidgetId()
        value = ds[wid]
        indexes = iter(self.forward_indexes)
        for val in self.forward_values:
            index = indexes.next()
            if val == value:
                ds[index] = value
                return
        ds['%s-%s' % (wid, value)] = True # use empty string to mean 'all'

InitializeClass(CPSToDoFilterWidget)

widgetRegistry.register(CPSToDoFilterWidget)

class CPSUserIdFilterWidget(FilterWidgetMixin, CPSWidget):
    """Put user id in datastructure. No validation or rendering.

    Useful, e.g, for security indexes, special filterings.
    """

    meta_type = "User Id Filter Widget"

    _properties = (
        {'id': 'title', 'type': 'string', 'mode': 'w',
         'label': 'Title'},
        {'id': 'prefix', 'type': 'selection', 'mode': 'w',
         'label': 'Prefix to put before user id',
         'select_variable': 'prefixes'},
        ) +  FilterWidgetMixin._properties[1:]

    prefix = ''
    prefixes = ('', 'user:')

    def prepare(self, ds, **kw):
        from AccessControl import getSecurityManager
        user_id = getSecurityManager().getUser().getId()
        ds[self.getWidgetId()] = self.prefix + user_id

InitializeClass(CPSUserIdFilterWidget)

widgetRegistry.register(CPSUserIdFilterWidget)

