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
from Products.CPSDashboards import utils

class UtilsTest(CPSTestCase):
    layer = CPSDashboardsLayer

    def test_renderUsersLayout(self):
        # preventing errors on wrong charsets
        # this will trigger an error in case of failure
        utils.serializeForCookie(object(), 'unicode')
        utils.serializeForCookie(object(), 'bachibouzouk')
        pif = utils.serializeForCookie('oulipista style powa', 'unicode')
        utils.unserializeFromCookie(pif, charset='on lui dira')

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(UtilsTest),))
