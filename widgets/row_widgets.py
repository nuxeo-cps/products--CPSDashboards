# (C) Copyright 2006-2007 Nuxeo SAS <http://nuxeo.com>
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
import re
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
                                              CPSBooleanWidget,
                                              CPSSelectWidget)
from Products.CPSSchemas.ExtendedWidgets import CPSDateTimeWidget
from Products.CPSSchemas.widgets.image import CPSImageWidget


logger = logging.getLogger('CPSDashboards.widgets.row_widgets')

def xlate(s, cpsmcat):
    """Does a translation."""
    if not s: # no need to waste time
        return s
    return cpsmcat(s)


class CPSTypeIconWidget(CPSWidget):
    """widget showing the icon associated to the object's portal_type. """
    meta_type = 'Type Icon Widget'

    def prepare(self, datastructure, **kw):
        """Prepare datastructure from datamodel."""
        dm = datastructure.getDataModel()
        if self.fields:
            datastructure[self.getWidgetId()] = dm[self.fields[0]]
        else:
            obj = dm.getObject()
            if obj is not None:
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
        title = cpsmcat(title)
        return renderHtmlTag('img', src=uri, alt=title)

InitializeClass(CPSTypeIconWidget)


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
        return escape(cpsmcat(state))


InitializeClass(CPSWorkflowVariableWidget)

class CPSReviewStateStringWidget(CPSStringWidget):
    """Special widget for the rendering of a string like the review state.
    """

    meta_type = 'Review State String Widget'

    def render(self, mode, datastructure, **kw):
        if mode != 'view':
            return ''
        value = datastructure[self.getWidgetId()]
        cpsmcat = getToolByName(self, 'translation_service')
        xlated = cpsmcat(value)
        return renderHtmlTag('span', css_class=value, contents=xlated)

InitializeClass(CPSReviewStateStringWidget)

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
     'label': 'Should the display of values be translated?'},
    {'id': 'onclick', 'type': 'string', 'mode': 'w',
     'label': 'onClick to put on anchor element (breaks popup mode)'},
    {'id': 'onmouseover', 'type': 'string', 'mode': 'w',
     'label': 'onMouseOver to put on anchor element'},
    {'id': 'onmouseout', 'type': 'string', 'mode': 'w',
     'label': 'onMouseOut to put on anchor element'},
    {'id': 'heading_level', 'type': 'int', 'mode': 'w',
     'label': 'Heading level (e.g, 2 to render in a <h2> or 0 for none)'}
    )

    is_display_i18n = False
    target = ''
    popup = False
    popup_width = 800
    popup_height = 600
    onmouseover = ''
    onmouseout = ''
    onclick = ''
    heading_level = 0

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

        if not params['href']:
            return escape(params['contents'])

        if self.popup:
            script = renderHtmlTag('script', type='text/javascript',
                                     contents=JS_OPENER % (self.popup_width,
                                                           self.popup_height,),
                                   )
            onclick = "return link_popup('%s', 'roles')" % params['href']
            params['onclick'] = onclick

        for add in ('onmouseover', 'onmouseout', 'onclick'):
            v = getattr(self, add)
            if v:
                params[add] = v

        res = renderHtmlTag('a', **params)

        hl = self.heading_level
        if hl:
            res = '<h%d>%s</h%d>' % (hl, res, hl)

        if self.popup:
            return script + res

        return res

InitializeClass(CPSQualifiedLinkWidget)


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
            today = kw.get('today')
            if today is None:
                today = datetime.today()
            datastructure[wid] = str((today-due).days)
        else: # ZCat or ZODB
            try:
                due = DateTime(due)
            except DateTime.SyntaxError:
                value = ''
            else:
                today = kw.get('today')
                if today is None:
                    today = DateTime()
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
            base_rendered = xlated
        return '<span class="%s">%s</span>' % (css_class, base_rendered)


InitializeClass(CPSTimeLeftWidget)


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

    icon_true = ''
    icon_false = ''

    def prepare(self, datastructure, **kw):
        """Prepare datastructure from datamodel.

        Special version that expects either a bool or a str-casted -bool.
        XXX Remove when there's a Lucene field for booleans.
        """

        dm = datastructure.getDataModel()
        value = dm[self.fields[0]]
        if isinstance(value, basestring):
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

        if not icon:
            return ''

        uri = utool.getBaseUrl() + icon

        cpsmcat = getToolByName(self, 'translation_service')
        label = cpsmcat(label)

        return renderHtmlTag('img', src=uri, alt=label)

InitializeClass(CPSIconBooleanWidget)


class CPSIconSelectWidget(CPSSelectWidget):
    """ A boolean widget that renders as an icon.

    TODO: backport as an option of CPS Select Widget. """

    meta_type = "Icon Select Widget"

    _properties = CPSSelectWidget._properties + (
        {'id': 'icons', 'type':'boolean', 'mode':'w',
         'label': 'Use icons for',},
        {'id': 'prefix', 'type':'string', 'mode':'w',
         'label': 'Prefix of your icons',},
        {'id': 'suffix', 'type':'string', 'mode':'w',
         'label': 'Suffix of icons (.png, .jpeg, .gif...)',},
        )
    icons=''
    prefix=''
    suffix=''

    def prepare(self, datastructure, **kw):
        """Prepare datastructure from datamodel.

        """

        dm = datastructure.getDataModel()
        value = dm[self.fields[0]]
        datastructure[self.getWidgetId()] = value

    def render(self, mode, datastructure, **kw):
        """Render in mode from datastructure.
        icon image is a boolean that indicate if you use an icon to represent the value.
        You must named icons with the same id where is used in the value of the id vocabulary 
        and replace the blank by '_' .
        <prefix><identifiant><suffix>
        """
        value = datastructure[self.getWidgetId()]
        if mode != 'view':
            return CPSSelectWidget.render(self, mode, datastructure, **kw)

        utool = getToolByName(self, 'portal_url')
        label = self.label
        if self.icons and value:
            icon = self.prefix+value.replace(' ' ,'_')+self.suffix
        else:
            icon = ''
        if not icon:
            return ''
        uri = utool.getBaseUrl() + icon

        cpsmcat = getToolByName(self, 'translation_service')
        label = cpsmcat(label)
        return renderHtmlTag('img', src=uri, alt=label)

InitializeClass(CPSIconSelectWidget)


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
            title = None
            if not mid.startswith(prefix):
                continue
            mid = mid[pref_len:]
            if mid.startswith('role:'):
                if l10n is not None:
                    title = l10n(mid)
                else:
                    title = mid
            else:
                entry = mdir._getEntry(mid, default=None)
                if entry is not None:
                    title = entry[title_field]
            if title is not None:
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


class CPSMultiBooleanWidget(CPSWidget):
    """Convert several boolean attributes in datamodel to a string.

    The first to be true triggers the corresponding string from
    displayed_values. The last elt from displayed_values is used as default
    """

    meta_type = "Multi Boolean Widget"

    _properties = CPSWidget._properties + (
        {'id': 'displayed_values', 'type': 'tokens', 'mode': 'w',
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
            rendered = cpsmcat(rendered)
        return rendered

InitializeClass(CPSMultiBooleanWidget)


class CPSEmailDisplayWidget(CPSStringWidget):
    """Display an email address"""

    meta_type = 'Email Display Widget'

    compound_email_pattern = re.compile(
        r"^(.*)(<([-\w_.'+])+@(([-\w])+\.)+([\w]{2,4})>)$")

    def renderEmailAddress(self, value, tag="address"):
        # TODO: remove hardcoded style
        return renderHtmlTag(tag, style="font-size: 90%", contents=value)

    def renderOneEmail(self, value):
        m = self.compound_email_pattern.match(value)
        if m:
            title = escape(m.group(1).strip())
            email = self.renderEmailAddress(escape(m.group(2)))

            return "%s<br/>%s" % (title, email)
        else:
            return self.renderEmailAddress(value)

    def render(self, mode, datastructure, **kw):
        if mode != "view":
            return ""
        value = datastructure[self.getWidgetId()].strip()
        return self.renderOneEmail(value)

InitializeClass(CPSEmailDisplayWidget)


class CPSEmailsDisplayWidget(CPSLinesWidget, CPSEmailDisplayWidget):
    """Display a list of email addresses"""

    meta_type = 'Emails Display Widget'

    view_mode_separator = "<br/>"

    def render(self, mode, datastructure, **kw):
        if mode != "view":
            return ""
        values = datastructure[self.getWidgetId()]
        rendered = (self.renderOneEmail(v.strip()) for v in values)
        return self.view_mode_separator.join(rendered)

InitializeClass(CPSEmailsDisplayWidget)


class CPSQuickDisplayDateTimeWidget(CPSDateTimeWidget):
    """A much less flexible widget for quick view mode rendering. """

    meta_type = 'Quick Display DateTime Widget'
    _properties = CPSWidget._properties + (
        {'id': 'render_format', 'type': 'string', 'mode': 'w',
         'label': 'Date & time format string'},
        {'id': 'render_format_i18n', 'type': 'boolean', 'mode': 'w',
         'label': 'Is format string to be translated?'},
        )

    render_format_i18n = False
    render_format = ''

    def prepare(self, ds, **kw):
        dm = ds.getDataModel()
        ds[self.getWidgetId()] = dm[self.fields[0]]

    def render(self, mode, datastructure, **kw):
        if mode not in ['search', 'view']:
            raise ValueError("This widget is for display only. ")
        value = datastructure[self.getWidgetId()]
        if value is None:
            return ''
        format = self.render_format
        if self.render_format_i18n:
            cpsmcat = getToolByName(self, 'translation_service')
            format = xlate(format, cpsmcat)
        return escape(value.strftime(format))

InitializeClass(CPSQuickDisplayDateTimeWidget)


class CPSImageWithLinkWidget(CPSImageWidget):
    """Display the image within an anchor element.

    Link is specified by the 'link_field' property.
    If empty, does same as Qualified Link Widget.

    For view mode only.
    """

    meta_type = "Image With Link Widget"
    _properties = CPSImageWidget._properties + (
        {'id': 'link_field', 'type': 'string', 'mode': 'w',
         'label': 'Field holding href'},
        )

    link_field = ''

    def prepare(self, ds, **kw):
        CPSImageWidget.prepare(self, ds, **kw)
        dm = ds.getDataModel()
        key = '%s_%s' % (self.getWidgetId(), 'href')
        if self.link_field:
            ds[key] = dm[self.link_field]
        else:
            proxy = dm.getProxy()
            if proxy is None:
                raise ValueError(
                    "No field provided for link, no proxy object found")
            utool = getToolByName(self, 'portal_url')
            base_url = utool.getBaseUrl()
            rpath = utool.getRpath(proxy)

            ds[key] = base_url+rpath

    def render(self, mode, ds, **kw):
        if mode != 'view':
            raise NotImplementedError

        anchor = '<a href="%s">' % escape(
            ds['%s_%s' % (self.getWidgetId(), 'href')])
        image = CPSImageWidget.render(self, mode, ds, **kw)
        return anchor + image + '</a>'

InitializeClass(CPSImageWithLinkWidget)

