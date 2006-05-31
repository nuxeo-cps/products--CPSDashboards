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

#$Id$

# testing module and harness

import unittest
from zope.testing import doctest

from Products.CPSCourrier.tests.layer import IntegrationTestCase
from Products.CPSCourrier.widgets.tabular import FakeRequestWithCookies

from Products.CMFCore.utils import getToolByName
from Products.CPSCourrier.browser.roadmapview import RoadmapView
from Products.CPSCourrier.browser.reuseanswerview import ReuseAnswerView
from Products.CPSCourrier.config import RELATION_GRAPH_ID, HAS_REPLY

class IntegrationTestRoadmapView(IntegrationTestCase):

    def afterSetUp(self):
        IntegrationTestCase.afterSetUp(self)
        self.request = FakeRequestWithCookies()
        dtool = getToolByName(self.portal, 'portal_directories')
        self.mdir = mdir = dtool.members
        mdir._createEntry({'id': 'test_roadmap_view', 'roles' : ['Manager',]})
        self.login('test_roadmap_view')
        self.wftool.doActionFor(self.in_mail1, 'handle')
        self.view = RoadmapView(self.in_mail1, self.request).__of__(
            self.portal)

    def beforeTearDown(self):
        self.mdir._deleteEntry('test_roadmap_view')
        IntegrationTestCase.beforeTearDown(self)

    def test_canManage(self):
        # reminder: we have Manager role
        self.assert_(self.view.canManage())

    def test_canMoveDown(self):
        # there's no level below
        self.failIf(self.view.canMoveDown())

        # let's build one
        self.wftool.doActionFor(self.in_mail1, 'manage_delegatees',
                                push_ids=['courrier_user:test_roadmap_view'],
                                levels=[-1],
                                current_wf_var_id='Pilots')

        self.assert_(self.view.canMoveDown())

    def test_renderStack(self):
        self.assert_(self.view.renderStack(mode='view'))

class IntegrationTestReuseAnswerView(IntegrationTestCase):

    def afterSetUp(self):
        IntegrationTestCase.afterSetUp(self)
        self.request = FakeRequestWithCookies()
        self.wftool.doActionFor(self.in_mail1, 'handle')
        self.view = ReuseAnswerView(self.in_mail1, self.request).__of__(
            self.portal)

    def test_dispatchSubmit(self):
        self.wftool.invokeFactoryFor(self.mb, 'Outgoing Mail', 'outgoing',
                                     content='template reply')
        outgoing = self.mb.outgoing
        self.request.form = {'rpath': '/'.join(['mailboxes',
                                               self.MBG_ID,
                                               self.MB_ID,
                                               'outgoing']),
                             'answer_submit' : 'go'}
        self.view.dispatchSubmit()

        # retrieve the answer (should factorize this)
        rtool = getToolByName(self.portal, 'portal_relations')
        outgoing_docids= rtool.getRelationsFor(RELATION_GRAPH_ID,
                                               int(self.in_mail1.getDocid()),
                                               HAS_REPLY)
        self.assertEquals(len(outgoing_docids), 1)
        docid = str(outgoing_docids[0])
        pxtool = getToolByName(self.portal, 'portal_proxies')
        proxies = pxtool.listProxies(docid=docid)
        self.assertEquals(len(proxies), 1)
        outgoing = self.portal.unrestrictedTraverse(proxies[0][0])

        self.assertEquals(outgoing.getContent().content, 'template reply')

    def test_dispatchSubmit_nothing(self):
        # The button isn't in the form, one shouldn't do anything
        self.request.form = {'sort-on': 'column', 'rpath': '/some/rpath'}
        self.assertEquals(self.view.dispatchSubmit(), '')


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(IntegrationTestRoadmapView),
        unittest.makeSuite(IntegrationTestReuseAnswerView),
        doctest.DocFileTest('doc/developer/views.txt',
                            package='Products.CPSCourrier'),
        doctest.DocFileTest('doc/developer/searchview.txt',
                            package='Products.CPSCourrier'),
        ))
