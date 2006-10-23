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

from Products.CPSDashboards.browser.searchview import SearchView

from Products.CMFCore.utils import getToolByName, _checkPermission
from Products.CMFCore.permissions import AddPortalContent

logger = logging.getLogger('CPSDashboards.browser.advancedsearchview')

class AdvancedSearchView(SearchView):

    layout_id = 'dashboard'

    def saveAsAllowed(self):
        """Check if saveas action is allowed."""

        mtool = getToolByName(self.context, 'portal_membership')
        home = mtool.getHomeFolder(verifyPermission=0)
        if home is None:
            return False

        max_allowed = mtool.getProperty('max_dashboards_allowed',
                                        5)
        num_dash = len([ob for ob in home.objectValues(['CPS Proxy Document'])
                        if ob.portal_type == 'Dashboard'])

        return num_dash < max_allowed and _checkPermission(AddPortalContent,
                                                           home)

    def dispatchSubmit(self):
        """take submissions, calls skins scripts, etc.

        returns rendered html, empty meaning no script called"""

        form = self.request.form

        form.pop('-C', None) # polluting key from publisher

        if 'saveas_submit' in form:
            method = 'cpsdocument_create_form'
            mtool = getToolByName(self.context, 'portal_membership')
            context = mtool.getHomeFolder(verifyPermission=1)
            meth = getattr(context, method)
            return meth(REQUEST=self.request)


