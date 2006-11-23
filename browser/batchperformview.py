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

import transaction

from urllib import urlencode
from logging import getLogger, DEBUG

from Acquisition import aq_inner, aq_parent
from OFS.CopySupport import CopyError
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CPSCore.EventServiceTool import getPublicEventService
from Products.CPSUtil.session import sessionHasKey
from Products.CPSUtil.timer import Timer

from searchview import SearchView

logger = getLogger('CPSDashboards.browser.batchperformview')


class BatchPerformView(SearchView):
    """A generic view class to perform batch actions on documents.

    It can be used in conjunction with a tabular widget, that renders buttons
    tied to CMF actions.

    There are mainly two cases:
        - non workflow actions, e.g, cut/copy/paste. It is assumed that
          right to perform has to be checked on context (ie the folder).
        - batch workflow transitions with a classical confirmation form. A
          prefiltering is applied to exclude documents for which the transition
          is not available.
        - session_key: sessions get used to keep bunches of rpaths from one
          screen to another.

    This is meant to be subclassed. Attributes to override are
       - non_wf_actions: you can register hear your handlers.
       - submit_button_prefix: the action to be done is deduced from the
       submit button's name, with this prefix cut out.

    Subclasses can be hooked as browser pages either
       - by using a different page name that the default one in CPSDashboards
       - by an overrides.zcml (this is terminal)

    Associated template:
       it must understand the 'do_redirect' response and use it to avoid
       costly and useless renderings.

       Note that .. is allowed in the templates path so that one can reuse one
       from CPSDashboards.
    """

    non_wf_actions = {'cut': '_doCutCopyPaste',
                      'copy': '_doCutCopyPaste',
                      'paste': '_doCutCopyPaste'}
    submit_button_prefix = "cpsdashboards_batch_"
    session_key = "CPSDASHBOARDS_BATCH_PERFORM"

    action = None # id of the action to be performed
    rpaths = () # rpaths of documents as target of the action

    #
    # Helpers to maintain current session
    #

    def _storeDataInSession(self, rpaths, action_id):
        """Store data in a session to allow for multi screen action"""
        request = self.request
        if not sessionHasKey(request, self.session_key):
            request.SESSION[self.session_key] = {}
        rpath = getToolByName(self.context, 'portal_url').getRpath(self.context)
        data = {
            'action_id': action_id,
            'rpaths': rpaths,
        }
        request.SESSION[self.session_key][rpath] = data

    def _readDataFromSession(self):
        """Read the request session to find stored rpaths"""
        request = self.request
        if not sessionHasKey(request, self.session_key):
            return [], None
        rpath = getToolByName(self.context, 'portal_url').getRpath(self.context)
        data = request.SESSION[self.session_key].get(rpath, {})
        return data.get('rpaths', []), data.get('action_id')

    def _expireSession(self):
        """Expire rpaths info related to the current mailbox"""
        request = self.request
        if not sessionHasKey(request, self.session_key):
            return
        rpath = getToolByName(self.context, 'portal_url').getRpath(self.context)
        del request.SESSION[self.session_key][rpath]

    def _filterMatchingRpaths(self, action, rpaths):
        """Helper method to filter out non p-matching rpaths"""
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        wftool = getToolByName(self.context, 'portal_workflow')
        filtered = []
        for rpath in rpaths:
            proxy = portal.unrestrictedTraverse(rpath)
            for wf in wftool.getWorkflowsFor(proxy):
                if wf.isActionSupported(proxy, action):
                    filtered.append(rpath)
        return filtered

    def _getSessionData(self):
        """Process the request to extract the list of rpaths and action id

        Also take care of storing/reading/updating the session if necessary
        """
        form = self.request.form

        # extract rpaths info from the request

        if 'ids' in form:
            utool = getToolByName(self.context, "portal_url")
            folder_rpath = utool.getRpath(self.context.aq_inner)
            rpaths =  ['%s/%s' % (folder_rpath, id) for id in form['ids']]
        else:
            rpaths = form.get('rpaths', ())

        # extract action id info from request

        actions = [key for key in form
                           if key.startswith(self.submit_button_prefix)]
        if len(actions) > 1:
            raise ValueError("Got more than one action to perform: %r" %
                             actions)
        if actions:
            action = actions[0][len(self.submit_button_prefix):]
        else:
            action = None

        if action is None or action not in self.non_wf_actions:
            # filter out non matching rpaths
            rpaths = self._filterMatchingRpaths(action, rpaths)

        # session management:
        #  - store data read from the request
        #  - read missing data previously stored

        # are we at the first call of the batch form or inside a multi screen
        # session?
        init_call = False
        for key in form:
            if key.startswith(self.submit_button_prefix):
                init_call = True
                break

        if not rpaths and not init_call:
            # nothing was provided in the request, we are probably in a multi
            # screens session:
            # try to see if data was previously stored in the session
            rpaths, action = self._readDataFromSession()
        else:
            # rpaths were directly provided in the request, store them in
            # cookies for later reuse
            self._storeDataInSession(rpaths, action)

        logger.debug('rpaths: %s, action_id: %s', rpaths, action)
        return rpaths, action

    #
    # Non workflow actions helpers
    #

    def _doRedirect(self, psm):
        """Perform a classical redirection. Avoid useless rendering."""
        url = "%s?%s" % (self.context.absolute_url(),
                         urlencode({'portal_status_message': psm}))
        self.request.RESPONSE.redirect(url)
        # flag that the template understands
        return 'do_redirect'

    #
    # Non workflow actions handlers
    #

    def _doCutCopyPaste(self):
        """Handling of cut/copy/paste actions

        Such handlers have to perform security checkings at the context level.
        They can be used for several actions.
        """
        if self.action == 'paste':
            if self.context.cb_dataValid:
                cp = self.request['__cp']
                try:
                    result = self.context.manage_CPSpasteObjects(cp)
                    for id in [ob['new_id'] for ob in result]:
                        ob = getattr(self.context, id)
                        evtool = getPublicEventService(self.context)
                        evtool.notifyEvent('workflow_cut_copy_paste', ob, {})
                    psm = 'psm_item(s)_pasted'
                except CopyError:
                    psm = 'psm_copy_or_cut_at_least_one_document'
                except WorkflowException:
                    psm = 'psm_operation_not_allowed'
            else:
                psm = 'psm_copy_or_cut_at_least_one_document'
        else:
            # copy or cut
            ids = [rpath.rsplit('/', 1)[1] for rpath in self.rpaths]
            if ids:
                if self.action == 'cut':
                    self.context.manage_CPScutObjects(ids, self.request)
                    psm = 'psm_item(s)_cut'
                if self.action == 'copy':
                    self.context.manage_CPScopyObjects(ids, self.request)
                    psm = 'psm_item(s)_copied'
            else:
                psm = 'psm_select_at_least_one_document'

        return self._doRedirect(psm)

    #
    # View API for the template
    #

    def dispatchSubmit(self):
        """Process the POST request of the tabular widget listing views
        """
        # compute the list of incoming mail rpath and store them as attribute
        # of the view instance
        self.rpaths, self.action = self._getSessionData()

        if not self.action:
            raise ValueError('No action specified')

        # non wf actions
        meth = self.non_wf_actions.get(self.action)
        if meth is not None:
            return getattr(self, meth)()

        if not self.rpaths:
            return self._doRedirect('psm_select_at_least_one_valid_item')

        trigger_transition = self.request.form.get('trigger_transition', None)
        if trigger_transition is not None:
            # handle the redirection and the psm
            return self.batchTriggerTransition(trigger_transition)

    def getDocumentInfo(self):
        """Compute data related to the rpath"""
        infos = []
        utool = getToolByName(self.context, 'portal_url')
        portal = utool.getPortalObject()
        for rpath in self.rpaths:
            proxy = portal.unrestrictedTraverse(rpath)
            container = aq_parent(aq_inner(proxy))
            infos.append({
                'title': proxy.Title(),
                'url': proxy.absolute_url(),
                'container_title': container.Title(),
                'container_url': container.absolute_url(),
            })
        return infos

    def batchTriggerTransition(self, transition, kwargs=None):
        """Do the WF update when possible and return the result as psm

        Optional kwargs dict is passed to the transition.
        """

        t = Timer('CPSDashboards.browser.batchperformview.batchTriggerTransition',
                  level=DEBUG)

        wftool = getToolByName(self.context, 'portal_workflow')
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        form = self.request.form

        kw = {
           'comment': form.get('comments', ''),
        }
        if kwargs is not None:
            kw.update(kwargs)

        t.mark('Process form data')

        failed = set()
        proxies = [portal.unrestrictedTraverse(rpath) for rpath in self.rpaths]

        t.mark('Grab proxies')

        for i, proxy in enumerate(proxies):
            wf = wftool.getWorkflowsFor(proxy)[0]

            if wf.isActionSupported(proxy, transition):
                wftool.doActionFor(proxy, transition, **kw)

                t.mark("Do action '%s' for proxy %d" % (transition, i))

                # each proxy is independant, thus commit to avoid conflict
                # errors on portal_proxies between two batch performers
                transaction.commit()

                t.mark('Commit for proxy %d' % i)

            else:
                failed.add(proxy)


        # this is the end of the batch session
        self._expireSession()

        t.mark('Expire session')

        # compute the psm according to what was actually done
        psm = "psm_status_changed"
        mcat = getToolByName(self.context, 'translation_service')
        if failed:
            # translating psm here because no interpolation can be done at
            # display time for psms
            psm = mcat("psm_no_action_performed_for")
            psm = psm.encode('iso-8859-15')
            psm += ', '.join(proxy.Title() for proxy in failed)

        t.mark('Compute psm')
        t.log()

        return self._doRedirect(psm)


