# (C) Copyright 2006 Nuxeo SAS <http://nuxeo.com>
# Author: G. Racinet <gracinet@nuxeo.com>
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
# $Id$

from Products.CMFCore.utils import getToolByName

from searchview import SearchView

class LocalRolesView(SearchView):

    # For redirections. Ideally the form template should read it from
    # its view instance and pass it along.
    form_name = 'folder_localroles.html'

    def __init__(self, *args):
        SearchView.__init__(self, *args)

        self.users_results = 'submit_users_search' in self.request.form
        self.groups_results = 'submit_groups_search' in self.request.form
        self.is_results = self.users_results or self.groups_results

    def renderResults(self):
        if self.users_results:
            return self.renderUsersLayout()
        if self.groups_results:
            return self.renderGroupsLayout()

    def renderUsersLayout(self):
        return self.renderLayout(name='localroles_users_search')['rendered']

    def renderGroupsLayout(self):
        return self.renderLayout(name='localroles_groups_search')['rendered']

    def checkPerm(self):
        mtool = getattr(self, 'mtool', None) or getToolByName(
            self.context, 'portal_membership')
        res = mtool.canMemberChangeLocalRoles(self.context)
        if not res:
            self.request.response.redirect(self.context.absolute_url())
        return res

    def dispatchSubmit(self):
        """Indirection to FS PythonsScript from skins."""
        self.checkPerm()
        form = self.request.form
        form.pop('-C', None) # polluting key from publisher
        # I'd prefer not this to be hardcoded here but I'd have to...
        # hardcode it in all templates and macros
        form_name = form.pop('form_name', 'folder_localroles.html')

        args = []
        if 'member_role' in form:
            meth = 'folder_localrole_add'
            args = [form.pop('member_role')]
        elif 'edit_local_roles' in form:
            meth = 'folder_localrole_edit'
        elif 'delete_local_roles' in form:
            meth = 'folder_localrole_edit'
        elif 'lr_block' in form or 'lr_unblock' in form:
            meth = 'folder_localrole_block'

        meth = getattr(self.context, meth)
        kwargs = form.copy()
        kwargs['REQUEST'] = self.request
        meth(*args, **kwargs)

        self.reRedirect('folder_localrole_form', new_target=form_name)

    def getCPSCandidateLocalRoles(self):
        mtool = getToolByName(self.context, 'portal_membership')
        return mtool.getCPSCandidateLocalRoles(self.context)
