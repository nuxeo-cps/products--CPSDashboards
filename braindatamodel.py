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
# $Id$

import logging
logger = logging.getLogger('CPSDashboards.braindatamodel')

from zope.interface import implements

from OFS.Image import File

from Products.CMFCore.utils import getToolByName

from Products.CPSCore.interfaces import ICPSProxy
from Products.CPSSchemas.DataModel import DataModel

class FakeDataModel(dict):
    pass

class FakeDocument:
    """ A pseudo document that can return a FakeDataModel."""
    def __init__(self, **kw):
        self._data = kw

    def getDataModel(self, **kw):
        dm = FakeDataModel(self._data)
        dm._adapters = ['the', 'fake', 'adapter']
        return dm

class FakeBrain:
    """ A pseudo brain out of a dict (for tests) """
    def __init__(self, d):
        for key, item in d.items():
            setattr(self, key, item)

    def getObject(self):
        return self._object

class FakeProxy(object):
    implements(ICPSProxy)

    def __init__(self, ob):
        self._content = ob

    def getContent(self):
        return self._content

_lazy = object()
_missing = object()

class BrainDataModel(DataModel):
    """ To use brain catalog results as a datamodel.

    This is basically an indirection to the brains attributes, plus some
    computed ones (url etc.).
    XXX GR leverage schema/adapters and use a regular datamodel ?

    >>> d = FakeBrain({'spam': 'eggs', 'a': 'b'})
    >>> dm =  BrainDataModel(d)
    >>> dm._brain == d
    True
    >>> dm['spam']
    'eggs'
    >>> dm.get('spam')
    'eggs'
    >>> dm['non']
    Traceback (most recent call last):
    ...
    KeyError: 'non'
    >>> dm['non'] = 0
    Traceback (most recent call last):
    ...
    NotImplementedError

    If data cannot be found in the brains, lookup goes on in object's datamodel.
    This is to be avoided for performance but probably necessary in case of
    files and images. Consequence: catching KeyError to see if some data exists
    can be costly.

    Let's take an attribute that doesn't exist in the brain:
    >>> dm._brain.foo
    Traceback (most recent call last):
    ...
    AttributeError: FakeBrain instance has no attribute 'foo'

    Now make let's set a proxy in the Brain. This is normally done by catalog
    >>> proxy = FakeProxy(FakeDocument(foo='bar'))
    >>> d._object = proxy
    >>> dm = BrainDataModel(d)
    >>> dm['foo']
    'bar'

    Adapters have been saved for the widgets that want to take a look at them:
    >>> dm._adapters
    ['the', 'fake', 'adapter']
    """


    def __init__(self, brain, context=None):
        self._brain = brain
        if context is None:
            self._context = self._brain
        else:
            self._context = context

        self._forbidden_widgets = []
        # for compat, we're not supposed to use acls anyway
        self._acl_cache_user = []
        self.data = {}

        self._brain_obj = _lazy
        self._object = _lazy
        self._proxy = _lazy

    def getObject(self):
        """ Return the object as if self was a regular datamodel. """

        if self._object is not _lazy:
            return self._object

        proxy = self.getProxy()
        if proxy is not None:
            obj = proxy.getContent()
        else:
            obj = self._brainGetObject()
        return obj

    def getProxy(self):
        if self._proxy is not _lazy:
            return self._proxy

        proxy = self._brainGetObject()
        if not ICPSProxy.providedBy(proxy):
            proxy = None

        self._proxy = proxy
        return proxy

    def _brainGetObject(self):
        if self._brain_obj is not _lazy:
            return self._brain_obj

        meth = getattr(self._brain, 'getObject', None)
        if meth is None:
            obj = None
        else:
            obj = meth()

        logger.debug("[PERFORMANCE] Retrieving object from ZODB")
        self._brain_obj = obj
        return obj

    def get(self, key, default=_missing):
        """Examples with callables:

        >>> dm = BrainDataModel(FakeBrain({}))
        >>> def smthing():
        ...    return True
        >>> dm._brain.smthing = smthing
        >>> dm.get('smthing')
        True
        """

        try:
            return self[key]
        except KeyError:
            if default is _missing:
                raise
            return default

    def __getitem__(self, key):
        """We read attributes from brain, even callables

        >>> dm = BrainDataModel(FakeBrain({}))
        >>> def smthing():
        ...    return True
        >>> dm._brain.smthing = smthing
        >>> dm['smthing']
        True
        """
        # If already computed, return value
        value = self.data.get(key)
        if value is not None:
            return value

        # not in cache
        try:
            value = getattr(self._brain, key)
        except AttributeError:
            # try and compute some values (see XXX in docstring for improvement)
            brain = self._brain
            if key == 'rpath':
                # GR. There is now a 'relative_path' brain attribute that
                # could be used instead of calling the URL tool
                utool = getattr(self, 'utool', None)
                if utool is None:
                     utool = getToolByName(self._brain, 'portal_url')
                     self.utool = utool
                value = utool.getRpathFromPath(brain.getPath())
            elif key == 'url':
                rpath = self.__getitem__('rpath')
                # we are now sure that self.utool has been set
                value = self.utool.getUrlFromRpath(rpath)
            else:
                logger.debug('Fetching field %s from ZODB', key)
                # fallback on object's datamodel
                dm = getattr(self, '_obj_dm', None)
                if dm is None:
                    try:
                        self._obj_dm = dm = self.getObject().getDataModel(
                            proxy=self.getProxy())
                    except AttributeError:
                        # should maybe return None ?
                        raise KeyError(key)
                # Image Widget requires this
                self._adapters = dm._adapters
                value = dm[key]

        if callable(value) and not isinstance(value, File):
            value = value()

        # remember value
        self.data[key] = value
        return value

    def __setitem__(self, key, item):
        raise NotImplementedError

    def checkWriteAccess(self, key):
        return False

    def checkReadAccess(self, key):
        return True
