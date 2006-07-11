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

# what we test
from Products.CPSDashboards import utils

class UtilsTest(unittest.TestCase):

    def test_serialization(self):
        start = {'abc' : '\xe9', 'a' : []}
        pif = utils.serializeForCookie(start, 'iso_8859_15')
        res = utils.unserializeFromCookie(pif, charset='iso_8859_15')
        self.assertEquals(res, {u'a': [], u'abc': u'\xe9'})

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(UtilsTest),))
