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

"""CPSDashboards utilities for unit tests."""
from Products.CPSDashboards.braindatamodel import FakeBrain

class FakeResponse:

    def __init__(self):
        self.cookies = {}
        self.headers = {}

    def getStatus(self):
        return self.status

    def redirect(self, url):
        self.headers['location'] = url
        self.status = 302

    def getHeader(self, key):
        return self.headers[key]

    def setCookie(self, cookie_id, cookie, path=None):
        self.cookies[cookie_id] = {
            'value': cookie, 'path': path}

    def expireCookie(self, arg, **kw):
        print "FakeResponse: called expireCookie with arg=%s" % arg



class FakeRequestWithCookies:
    """To simulate a request with cookies

    Note: the dict API is not well implemented (no diff between [] and get)

    >>> request = FakeRequestWithCookies()
    >>> request.form
    {}
    >>> request['KEY'] = 'spam'
    >>> request['KEY']
    'spam'
    >>> request.get('KEY')
    'spam'
    >>> request.get('NOKEY') is None
    True
    >>> request.RESPONSE.setCookie('cook_id', 'contents')
    """

    def __init__(self, **kw):
        self.form = kw
        self.cookies = {}
        self.RESPONSE = FakeResponse()
        self.URLPATH1 = '/path/to/obj'
        self.other = {} # holds sessions

    def __getitem__(self, key, default=None):
        return getattr(self, key, default)

    def get(self, key, default=None):
        return self.__getitem__(key, default=default)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def getCookie(self, cookie_id, **kw):
        """ We do nothing about the path currently."""

        info = self.cookies.get(cookie_id)
        if info is None:
            return None
        return info['value']

class FakeLuceneCatalog:

    @classmethod
    def _makeBrain(self, i, out_of=10):
        brain = FakeBrain({'Title': 'Title %d' % i,
                           'content': 'content %d' % i,
                           'Description': ''})
        brain.out_of = out_of
        return brain

    _nb_results = 0
    wrong_out_of = 0

    def setNbResults(self, nb):
        self._nb_results = nb

    def __call__(self, b_start=0, b_size=10, **kw):
        out_of = self.wrong_out_of or self._nb_results
        return [self._makeBrain(i, out_of=out_of)
                for i in range(self._nb_results)[b_start:b_start+b_size]]

