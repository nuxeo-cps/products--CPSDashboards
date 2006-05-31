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

""" This module holds simple widget definitions for CPSDashboards row layouts.
"""
import logging
from cgi import escape
from datetime import datetime
from Globals import InitializeClass
from DateTime import DateTime

from Products.CMFCore.utils import getToolByName
from Products.CPSSchemas.Widget import CPSWidget
from Products.CPSSchemas.Widget import widgetRegistry
from Products.CPSSchemas.BasicWidgets import renderHtmlTag
from Products.CPSSchemas.BasicWidgets import (CPSStringWidget,
                                              CPSLinesWidget,
                                              CPSIntWidget,
                                              CPSBooleanWidget)

logger = logging.getLogger('CPSDashboards.widgets.row_widgets')

def xlate(s, cpsmcat):
    """Does a translation."""
    if not s: # no need to waste time
        return s
    return cpsmcat(s).encode('iso-8859-15')


class CPSTypeIconWidget(CPSWidget):
    """widget showing the icon associated to the object's portal_type. """
    meta_type = 'Type Icon Widget'

    def prepare(self, datastructure, **kw):
        """Prepare datastructure from datamodel."""
        dm = datastructure.getDataModel()
        obj = dm.getObject()
        if obj is None:
            return
        datastructure[self.getWidgetId()] = obj.portal_type

    def validate(self, datastructure, **kw):
        """Validate datastructure and update datamodel."""
        return 1

    def render(self, mode, datastructure, **kw):
        """Render in mode from datastructure."""

        ptype = datastructure.get(self.getWidgetId())
        if ptype is None:
            return ''

        ttool = getToolByName(self, 'portal_types')
        fti = getattr(ttool, ptype)
        icon = fti.getIcon()

        utool = getToolByName(self, 'portal_url')
        uri = utool.getBaseUrl() + icon
        title = fti.title_or_id()
        cpsmcat = getToolByName(self, 'translation_service')
        title = cpsmcat(title).encode('iso-8859-15')
        return renderHtmlTag('img', src=uri, alt=title)


InitializeClass(CPSTypeIconWidget)

widgetRegistry.register(CPSTypeIconWidget)

class CPSWorkflowVariableWidget(CPSWidget):
    """widget showing the value of a workflow_variable.

    By default this is review_state.
    """

    meta_type = 'Workflow Variable Widget'

    _properties = CPSWidget._properties + (
        {'id': 'wf_var_id', 'type' : 'string', 'mode' : 'w',
         'label': 'Name of the workflow variable to pick'},
        )

    wf_var_id = 'review_state'

    def prepare(self, datastructure, **kw):
        """Prepare datastructure from workflow var."""

        dm = datastructure.getDataModel()
        proxy = dm.getProxy()
        if proxy is None:
            return ''
        wftool = getToolByName(self, 'portal_workflow')
        datastructure[self.getWidgetId()] = wftool.getInfoFor(proxy,
                                                              self.wf_var_id)

    def validate(self, datastructure, **kw):
        """Validate datastructure and update datamodel."""
        return 1

    def render(self, mode, datastructure, **kw):
        """Render in mode from datastructure."""

        state = datastructure[self.getWidgetId()]
        if state is None:
            return ''
        cpsmcat = getToolByName(self, 'translation_service')
        return escape(cpsmcat(state).encode('iso-8859-15'))


InitializeClass(CPSWorkflowVariableWidget)

widgetRegistry.register(CPSWorkflowVariableWidget)

class CPSReviewStateStringWidget(CPSStringWidget):
    """Special widget for the rendering of a string like the review state.
    """

    meta_type = 'Review State String Widget'

    def render(self, mode, datastructure, **kw):
        if mode != 'view':
            return ''
        value = datastructure[self.getWidgetId()]
        cpsmcat = getToolByName(self, 'translation_service')
        xlated = cpsmcat(value).encode('iso-8859-15')
        return renderHtmlTag('span', css_class=value, contents=xlated)

InitializeClass(CPSReviewStateStringWidget)

widgetRegistry.register(CPSReviewStateStringWidget)

## XXX This should be part of CPSDefault std js libraries
# check status after current js refactorings
# As is, the script will be defined for each bloody widget calling it !
JS_OPENER = """function link_popup(url, name) {
       str_window_features = 'toolbar=0,scrollbars=0,location=0,statusbar=0,menubar=0,resizable=1,dependent=1,width=%d,height=%d'
       popup = window.open(url, name, str_window_features);
       if (!popup.opener) {
         popup.opener = window;
       }
       return false;
     }
"""

class CPSQualifiedLinkWidget(CPSWidget):
    """widget that makes a single <a> tag out of three informations.

    If only two fields are provided they are used as text and optional text.
    If there's a third, it holds the link destination (absolute).
    Otherwise the widget uses the proxy's url.
    """

    meta_type = 'Qualified Link Widget'

    field_types = ('CPS String Field', 'CPS String Field', 'CPS String Field')

    _properties = CPSWidget._properties + (
    {'id': 'target', 'type': 'string', 'mode': 'w',
     'label': 'Target attribute of <a> element'},
    {'id': 'popup', 'type': 'boolean', 'mode': 'w',
     'label': 'Should the link open a popup?'},
    {'id': 'popup_width', 'type': 'int', 'mode': 'w',
     'label': 'Width of popup window'},
    {'id': 'popup_height', 'type': 'int', 'mode': 'w',
     'label': 'Height of popup window'},
    {'id': 'is_display_i18n', 'type': 'boolean', 'mode': 'w',
     'label': 'Should the display of values be translated?'},)

    is_display_i18n = False
    target = ''
    popup = False
    popup_width = 800
    popup_height = 600

    def prepare(self, datastructure, **kw):
        """Prepare datastructure from datamodel."""

        w_id = self.getWidgetId()
        dm = datastructure.getDataModel()

        suffixes = ('contents', 'title', 'href')
        for suffix, fid in zip(suffixes, self.fields):
            datastructure['%s_%s' % (w_id, suffix)] = dm[fid]
        if len(self.fields) < 3: # no url field
            proxy = dm.getProxy()
            if proxy is None:
                raise ValueError(
                    "No field provided for link, no proxy object found")
            utool = getToolByName(self, 'portal_url')
            base_url = utool.getBaseUrl()
            rpath = utool.getRpath(proxy)

            datastructure['%s_%s' % (w_id, 'href')] = base_url+rpath

    def validate(self, datastructure, **kw):
        """Validate datastructure and update datamodel."""
        return 1

    def render(self, mode, datastructure, **kw):
        """Render in mode from datastructure."""

        w_id = self.getWidgetId()
        params = dict((suffix, datastructure['%s_%s' % (w_id, suffix)])
                       for suffix in ('href', 'title', 'contents',))
        if self.is_display_i18n:
            cpsmcat = getToolByName(self, 'translation_service')
            for key in ['title', 'contents']:
                params[key] = xlate(params[key], cpsmcat)
        if self.target:
            params['target'] = self.target

        if self.popup:
            script = renderHtmlTag('script', type='text/javascript',
                                     contents=JS_OPENER % (self.popup_width,
                                                           self.popup_height,))
            onclick = "return link_popup('%s', 'roles')" % params['href']
            params['onClick'] = onclick

        a_tag = renderHtmlTag('a', **params)

        if self.popup:
            return script + a_tag
        return a_tag

InitializeClass(CPSQualifiedLinkWidget)

widgetRegistry.register(CPSQualifiedLinkWidget)

class CPSRowBooleanWidget(CPSWidget):
    """widget making a checkbox or radio in a row.

    In case of checkbox, this allows to post a list.
    In radio, this allows to select from the rows.

    This will probably be extended in the future to take complex visibility
    conditions into account.

    If no field provided, try and find the associated proxy's id for the value
    otherwise pick the field value.
    """

    meta_type = 'Row Boolean Widget'

    _properties = CPSWidget._properties + (
        {'id': 'input_name', 'type' : 'string', 'mode' : 'w',
         'label': 'Name of the posted list', 'is_required': 1},
        {'id': 'input_type', 'type' : 'string', 'mode' : 'w',
         'label': 'Type of input element to render', 'is_required': 1},
        {'id': 'format_string', 'type' : 'string', 'mode' : 'w',
         'label': 'A python format string to apply to the field'},
        )

    list_name = ''
    format_string = ''

    def prepare(self, datastructure, **kw):
        """Prepare datastructure. """

        dm = datastructure.getDataModel()
        if self.fields:
            value = dm[self.fields[0]]
        else:
            proxy = dm.getProxy()
            if proxy is None:
                raise ValueError(
                    "No field, and datamodel is not associated to a proxy")
            value = proxy.getId()
        datastructure[self.getWidgetId()] = value

    def validate(self, datastructure, **kw):
        """Validate datastructure and update datamodel."""
        return 1

    def render(self, mode, datastructure, **kw):
        """Render in mode from datastructure."""

        if self.input_type == 'checkbox':
            name = '%s:list' % self.input_name
        elif self.input_type == 'radio':
            name = self.input_name
        else:
            raise ValueError("Unknown input type: %s" % self.input_type)
        value = datastructure[self.getWidgetId()]
        if self.format_string:
            value = self.format_string % value
        # XXX: content_lib_info_detail_tab uses  item.getContextUrl(utool=utool)
        # investigate ?
        return renderHtmlTag('input', type=self.input_type,
                             name=name, value=value)


InitializeClass(CPSRowBooleanWidget)

widgetRegistry.register(CPSRowBooleanWidget)

class CPSTimeLeftWidget(CPSIntWidget):
    """ A widget that displays time left.

    This is a temporary hack: won't be necessary once the braindatamodel
    thing has all schemas features, like read_process_expr
    """

    _properties = CPSIntWidget._properties + (
    {'id': 'is_display_i18n', 'type': 'boolean', 'mode': 'w',
     'label': 'Should the display of the value be translated?'},)

    is_display_i18n = False

    meta_type = 'Time Left Widget'

    def prepare(self, datastructure, **kw):
        dm = datastructure.getDataModel()
        wid = self.getWidgetId()
        due = dm[self.fields[0]]

        if isinstance(due, datetime): # Lucene
            today = kw.get('today', datetime.today())
            datastructure[wid] = str((today-due).days)
        else: # ZCat or ZODB
            try:
                due = DateTime(due)
            except DateTime.SyntaxError:
                value = ''
            else:
                today = kw.get('today', DateTime())
                value = str(int(today-due))
            datastructure[self.getWidgetId()] = value

    def render(self, mode, datastructure, **kw):
        base_rendered = CPSIntWidget.render(self, mode, datastructure)
        if mode != 'view':
            return base_rendered

        value = int(datastructure[self.getWidgetId()])
        plus_sign = value > 0 and '+' or ''

        #XXX use a property of the widget instead of hardcoded values
        if value  >= -5:
            css_class = 'late'
        elif value in range(-10, -5): # -5 excluded
            css_class = 'shortly'
        else:
            css_class = 'inTime'

        if self.is_display_i18n:
            cpsmcat = getToolByName(self, 'translation_service')
            xlated = cpsmcat('cpscourrier_timeleft:${plus_sign}${d}',
                                    {'d': base_rendered,
                                    'plus_sign': plus_sign})
            base_rendered = xlated.encode('iso-8859-15')
        return '<span class=%s>%s</span>' % (css_class, base_rendered)


InitializeClass(CPSTimeLeftWidget)
widgetRegistry.register(CPSTimeLeftWidget)

class CPSIconBooleanWidget(CPSBooleanWidget):
    """ A boolean widget that renders as an icon.

    TODO: backport as an option of CPS Boolean Widget. """

    meta_type = "Icon Boolean Widget"

    _properties = CPSBooleanWidget._properties + (
        {'id': 'icon_true', 'type':'string', 'mode':'w',
         'label': 'Icon to display if value is True',},
        {'id': 'icon_false', 'type':'string', 'mode':'w',
         'label': 'Icon to display if value is False',}
        )

    def prepare(self, datastructure, **kw):
        """Prepare datastructure from datamodel.

        Special version that expects either a bool or a str-casted -bool.
        XXX Remove when there's a Lucene field for booleans.
        """

        dm = datastructure.getDataModel()
        value = dm[self.fields[0]]
        if isinstance(value, str):
            value = bool(int(value))
        else:
            value = bool(value)
        datastructure[self.getWidgetId()] = value

    def render(self, mode, datastructure, **kw):
        """Render in mode from datastructure."""
        value = datastructure[self.getWidgetId()]
        if mode != 'view':
            return CPSBooleanWidget.render(self, mode, datastructure, **kw)

        utool = getToolByName(self, 'portal_url')
        if value:
            icon = self.icon_true
            label = self.label_true
        else:
            icon = self.icon_false
            label = self.label_false
        uri = utool.getBaseUrl() + icon

        cpsmcat = getToolByName(self, 'translation_service')
        label = cpsmcat(label).encode('iso-8859--15')

        return renderHtmlTag('img', src=uri, alt=label)

InitializeClass(CPSIconBooleanWidget)
widgetRegistry.register(CPSIconBooleanWidget)

class CPSUsersWithRolesWidget(CPSLinesWidget):
    """A widget that displays the list of users having one of the given roles.

    BaseDirectory's title_field prop is used to represent users
    Doesn't support groups yet
    """

    meta_type = 'Users With Roles Widget'

    _properties = CPSWidget._properties + (
        {'id': 'roles', 'type' : 'tokens', 'mode' : 'w',
         'label': 'Roles to look for', 'is_required': 1},
        {'id': 'merge_roles', 'type' : 'boolean', 'mode' : 'w',
         'label': 'Take roles inherited into account?'},
        )

    roles = []
    merge_roles = False

    def _hasRequiredRoles(self, member_info):
        """Analyses the contets."""
        return False

    def _extractMembers(self, prefix, mdir, members, l10n=None):
        """Convert member id as returned by Membership Tool.
        """

        pref_len = len(prefix)
        title_field = mdir.title_field

        res = []
        for mid in members:
            if not mid.startswith(prefix):
                continue
            mid = mid[pref_len:]
            if mid.startswith('role:'):
                if l10n is not None:
                    title = l10n(mid).encode('iso-8859-15')
                else:
                    title = mid
            else:
                title = mdir._getEntry(mid)[title_field]
            res.append(title)
        return res

    def prepare(self, datastructure, **kw):
        proxy = datastructure.getDataModel().getProxy()

        if not self.merge_roles:
            raise NotImplementedError
        wanted_roles = set(self.roles)
        mtool = getToolByName(self, 'portal_membership')

        roles_info = mtool.getMergedLocalRoles(proxy)
        logger.debug(roles_info)
        members = [mid for mid, m_roles in roles_info.items()
                   if wanted_roles.intersection(m_roles)]

        if not members:
            datastructure[self.getWidgetId()] = []
            return

        aclu = getToolByName(self, 'acl_users')
        dtool = getToolByName(self, 'portal_directories')
        if aclu.meta_type == 'CPS User Folder':
            udir_id = aclu.users_dir
            gdir_id = aclu.groups_dir
        else:
            udir_id = 'members'
            gdir_id = 'groups'
        udir = dtool[udir_id]
        gdir = dtool[gdir_id]
        l10n = getToolByName(self, 'translation_service')
        users = self._extractMembers('user:', udir, members, l10n=l10n)
        groups = self._extractMembers('group:', gdir, members, l10n=l10n)

        lines = users + groups
        logger.debug(lines)
        datastructure[self.getWidgetId()] = lines


InitializeClass(CPSUsersWithRolesWidget)
widgetRegistry.register(CPSUsersWithRolesWidget)

class CPSMultiBooleanWidget(CPSWidget):
    """Convert several boolean attributes in datamodel to a string."""

    meta_type = "Multi Boolean Widget"

    _properties = CPSWidget._properties + (
        {'id': 'displayed_values', 'type': 'string', 'mode': 'w',
         'label': 'Values corresponding to fields to be displayed '},
        {'id': 'is_display_i18n', 'type': 'boolean', 'mode': 'w',
         'label': 'Are displayed values to be translated?'},
        )

    displayed_values = ()
    is_display_i18n = False

    def prepare(self, datastructure, **kw):
        dm = datastructure.getDataModel()
        for c, f_id in enumerate(self.fields):
            if dm.get(f_id):
                value = self.displayed_values[c]
                break
        else:
            value = self.displayed_values[len(self.fields)]
        datastructure[self.getWidgetId()] = value

    def render(self, mode, datastructure, **kw):
        if mode not in ['search', 'view']:
            raise NotImplementedError
        rendered = datastructure[self.getWidgetId()]
        if self.is_display_i18n:
            cpsmcat = getToolByName(self, 'translation_service')
            rendered = cpsmcat(rendered).encode('iso-8859-15')
        return rendered

InitializeClass(CPSMultiBooleanWidget)
widgetRegistry.register(CPSMultiBooleanWidget)

