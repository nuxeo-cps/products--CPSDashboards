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

import base64

from Products.CPSSkins import minjson as json

# based on CPSSkins versions, but can handle non ascii-chars
# here not to break possible CPSSkins assumptions

# XXX since we eventually patched both, we could settle for utf8, which
# json.read seems to assume by default
def serializeForCookie(obj, charset='ascii'):
    """Convert a python data structure into a base64 encoded string suitable
    for storing in a cookie."""

    string = json.write(obj)
    # base64 will cast to str, producing Unicode errors
    if isinstance(string, unicode):
        string = string.encode(charset)
    v = base64.encodestring(string)
    return v.replace('\n', '') # cookie values cannot contain newlines

def unserializeFromCookie(string='', default=None, charset='ascii'):
    """Convert a base64 string into a python object"""

    value = default
    if not string:
        return value

    # If not already unicode, myjson will try to decode assuming utf-8
    v = base64.decodestring(string).decode(charset)
    try:
        value = json.read(v)
    except IndexError:
        pass

    return value
