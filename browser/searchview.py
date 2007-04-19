# Copyright (c) 2006 Nuxeo SAS <http://nuxeo.com>
# Authors: Georges Racinet <gracinet@nuxeo.com>
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

import logging

from Products.Five.browser import BrowserView

from Products.CMFCore.utils import getToolByName

from Products.CPSSchemas.Widget import widgetname
from Products.CPSSchemas.BasicWidgets import renderHtmlTag
from Products.CPSDashboards.utils import unserializeFromCookie

logger = logging.getLogger('CPSDashboards.browser.searchview')

class SearchView(BrowserView):
    """This class if a helper base class for search forms and results.

    It provides the harness to call a layout in 'edit' mode to render the form
    and in 'search_results' mode to render the results.
    The call is provided by the renderLayout method and can be used like this:

    <tal:block replace="structure view/renderLayout"/>

    provided that the concrete subclass instance has a 'layout_id' attribute.
    An optional 'schema_id' attribute can be provided, too.
    Views that need to render several search forms can override this behaviour
    (see localrolesview for an example)

    ASSUMPTIONS:
      - the tabular widget's filter_button property is set to 'filter'
      - the name of associated page templates search button is 'search_submit'
    """

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        form = self.request.form
        self.is_results = 'search_submit' in form or 'filter' in form
        self.charset = self.context.default_charset

    def getId(self):
        """Return name as declared in ZCML.

        Use case: this will become the value of 'published'
        in portlet guards."""
        return self.__name__

    def setAttrs(self, **kw):
        """Set attributes.

        Useful in zpts where a lot of possibly costly info has already been
        looked up by a master macro."""

        for key, item in kw.items():
            setattr(self, key, item)

    def renderLayout(self, name='', schema_id=None):
        """Render the requested layout.

        Uses by default the schema of same name."""

        layout_id = name or self.layout_id
        schema_id = schema_id or getattr(self, 'schema_id', '') or layout_id
        mode = self.is_results and 'search_results' or 'edit'
        ltool = getToolByName(self.context, 'portal_layouts')
        # XXX the cookie stuff could be done by passing the right mapping here
        ob = {}
        rendered, status, ds = ltool.renderLayout(
            layout_id=layout_id,
            schema_id=schema_id,
            context=self.context,
            mapping=self.request.form,
            layout_mode=mode,
            ob=ob)
        logger.debug('status: %s' % status)
        return {'rendered': rendered, 'status': status, 'ds': ds}

    def forwardInputs(self, widgets, cookie_id=None):
        """make some hidden <input> tags to forward part request to next
        submission, in particular, parts of query that aren't cookie-persistent

        If we come from a column sort request, we have to pick the value
        from cookie (!)
        """

        res = []
        if cookie_id is not None:
            cookie = self.request.cookies.get(cookie_id)
        else:
            cookie = None
        if cookie is not None:
            cookie = unserializeFromCookie(cookie, charset=self.charset)
        for wid in widgets:
            name = widgetname(wid)
            if cookie is not None:
                value = str(cookie.get(wid))
            if cookie is None or value is None:
                value = self.request.form.get(name)
            if value is not None:
                tag = renderHtmlTag('input', type='hidden',
                                    name=name, value=value)
                res.append(tag)
        return '\n'.join(res)

    def getFormName(self):
        """Used by ZPT to know its own name in URL."""

        return str(self.__name__)

    def reRedirect(self, old_targets, new_target=None):
        """Rewrite redirection.

        In case we had to call one of CPS's standard FS PythonScripts,
        we might want to update the redirection it likely performed,
        keeping psms etc.

        The default new target is ourselves, which is relevant only if the form
        is designed to post on itself (like cpsdocument_edit_form for instance)
        """

        new_target = new_target or self.getFormName()
        response = self.request.RESPONSE
        if isinstance(old_targets, str):
            old_targets = [old_targets]

        if response.getStatus() == 302: # Moved temporarily (redirection)
            response.setHeader('Cache-Control', 'no-cache')
            url = response.getHeader('location')
            for old_target in old_targets:
                url = url.replace(old_target, new_target)
            response.redirect(url)

    def dispatchSubmit(self):
        """take submissions, calls skins scripts, etc.

        Implemented by base class.
        """

        raise NotImplementedError
