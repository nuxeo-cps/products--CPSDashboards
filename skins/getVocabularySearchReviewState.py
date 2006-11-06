##parameters=key=None, is_i18n=True
#$Id$
"""Return a list of review state, used as MethodVocabulary.

This script overrides the one from CPSDefault: translation and empty key were
delegated to the widgets. Original one kept unchanged for backwards compat.
"""

names = context.getWorkflowStateNames()
res = zip(names, names)

if key is not None:
    res = [item[1] for item in res if item[0] == key][0]

return res
