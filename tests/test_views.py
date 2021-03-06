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
from Products.CPSDefault.tests.CPSTestCase import CPSTestCase
from Products.CPSDashboards.testing import FakeRequestWithCookies
from layer import CPSDashboardsLayer

# what we test
from Products.CPSDashboards.browser.localrolesview import LocalRolesView

class LocalRolesViewIntegrationTestCase(CPSTestCase):
    layer = CPSDashboardsLayer

    def afterSetUp(self):
        self.request = FakeRequestWithCookies()
        self.view = LocalRolesView(self.portal.workspaces,
                                   self.request).__of__(self.portal)

    def test_renderUsersLayout(self):
        # just check config consistency

        self.view.renderUsersLayout()

    def test_renderGroupsLayout(self):
        # just check config consistency

        self.view.renderGroupsLayout()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(LocalRolesViewIntegrationTestCase),
        doctest.DocFileTest('doc/developer/views.txt',
                            package='Products.CPSDashboards'),
        doctest.DocFileTest('doc/developer/searchview.txt',
                            package='Products.CPSDashboards'),
        ))
