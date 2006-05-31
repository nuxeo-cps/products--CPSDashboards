# Copyright (c) 2006 Nuxeo SAS <http://nuxeo.com>
# Author : Georges Racinet <gracinet@nuxeo.com>
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
import unittest
from Testing import ZopeTestCase
from Products.GenericSetup import profile_registry
from Products.GenericSetup import EXTENSION
from Products.CMFCore.utils import getToolByName
from Products.CPSCore.interfaces import ICPSSite


from Products.CPSSchemas.tests.testWidgets import (
    FakeDataModel, FakeDataStructure, fakePortal,
    )
from Products.CPSDefault.tests.CPSTestCase import (
    CPSTestCase,
    ExtensionProfileLayerClass)

from Products.CPSDashboards.tests import widgets

# register profiles
ZopeTestCase.installProduct('CPSDashboards')

# CPSDashboards:tests : add more layouts to test the widgets
profile_registry.registerProfile(
    'tests',
    'CPS Dashboards Tests',
    "Tests of mail tracking and management system for CPS",
    'tests/profile',
    'CPSDashboards',
    EXTENSION,
    for_=ICPSSite)


class CPSDashboardsLayerClass(ExtensionProfileLayerClass):
    extension_ids = ('CPSDashboards:default', 'CPSDashboards:tests',)

CPSDashboardsLayer = CPSDashboardsLayerClass(
    __name__,
    'CPSDashboardsLayer'
    )
