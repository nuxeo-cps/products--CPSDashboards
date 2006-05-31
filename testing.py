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

class FakeResponse:

    def __init__(self):
        self.cookies = {}

    def setCookie(self, cookie_id, cookie, path=None):
        self.cookies[cookie_id] = {
            'value': cookie, 'path': path}

    def expireCookie(self, arg, **kw):
        print "FakeResponse: called expireCookie with arg=%s" % arg



class FakeRequestWithCookies:
    """To simulate a request with cookies

    >>> request = FakeRequestWithCookies()
    >>> request.form
    {}
    >>> request['KEY'] = 'spam'
    >>> request['KEY']
    'spam'
    >>> request.RESPONSE.setCookie('cook_id', 'contents')
    """

    def __init__(self, **kw):
        self.form = kw
        self.cookies = {}
        self.RESPONSE = FakeResponse()
        self.URLPATH1 = '/path/to/obj'

    def __getitem__(self, key, default=None):
        return getattr(self, key, default)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def getCookie(self, cookie_id, **kw):
        """ We do nothing about the path currently."""

        info = self.cookies.get(cookie_id)
        if info is None:
            return None
        return info['value']
