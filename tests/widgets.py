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

""" This module defines some concrete widget implementations for base classes
that will be loaded via test profile in the CPSCourrier test layer.

Therefore they have to be outside of integration test modules."""

from Globals import InitializeClass

from Products.CPSSchemas.Widget import widgetRegistry
from Products.CPSSchemas.DataStructure import DataStructure

from Products.CPSCourrier.braindatamodel import FakeBrain, BrainDataModel
from Products.CPSCourrier.widgets.tabular import TabularWidget


class TestingTabularWidget(TabularWidget):
    """ A subclass to implement listRowDataStructures.

    tests have to put parameters directly in datastructure.
    """

    meta_type = 'Testing Tabular Widget'

    brains = [FakeBrain(d) for d in [
        {'Title' : 'Title 1', 'content' : 'Pending', 'Description' : '',},
        {'Title' : 'Title 2', 'content' : 'Rejected', 'Description' : '',},
        ]]

    longbrains = [FakeBrain({'Title': 'Title %d' % i,
                             'content': 'content %d' % i,
                             'Description': ''}) for i in range(31)]

    def updateFilters(self, datastructure, **filts):
        """write filters to datastructure."""
        prefix = self.filter_prefix
        datastructure.update(dict((prefix + key, value)
                                  for key, value in filts.items()))

    def listRowDataStructures(self, datastructure, row_layout, **kw):
        if datastructure.get('longbrains'):
            b_page, b_start, b_size = self.getBatchParams(datastructure)
            nb_results = len(self.longbrains)
            brains = self.longbrains[b_start:b_start+b_size]
        else: # we don't test batching
            b_page = b_start = 1
            b_size = 10000
            nb_results = len(self.brains)
            brains = self.brains

        gendss = (DataStructure(datamodel=BrainDataModel(brain))
                              for brain in brains)
        return ((self.prepareRowDataStructure(row_layout, ds) for ds in gendss),
                b_page, self.getNbPages(nb_results))

InitializeClass(TestingTabularWidget)
widgetRegistry.register(TestingTabularWidget)
