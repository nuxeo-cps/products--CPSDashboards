##parameters=key=None, is_i18n=False
#$Id$
"""Return a portal type vocabulary, used as MethodVocabulary.

This script overrides the one from CPSDefault: translation and empty key were
delegated to the widgets. Original one kept unchanged for backwards compat.
"""

types = context.getSortedContentTypes(allowed=0)
if is_i18n:
    res = [(item['id'], item['Title'])
           for item in types]
else:
    # we use the id as label, better than nothing
    res = [item['id'] for item in types]
    res = zip(res, res)

if key is not None:
    res = [item[1] for item in res if item[0] == key][0]

return res
