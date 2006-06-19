CPSDashboards
=============

:Revision: $Id$

.. contents:: :depth: 2
.. sectnum::

Overview
--------

This product allows to build flexible and easily configurable search results
views of many kinds by leveraging the schema/layout architecture. It
includes support for batching, post-filtering and cookie-based
persistence.

The typical use case is the *personal dashboard*. This would be a
special document that stores personal search criteria and displays the
matching documents in view mode as a table with relevant information
in its columns.

In a CPS Default site, the following pages could leverage
CPSDashboards facilities:

* Advanced search form & results
* Local roles management form (users search part)
* Member directories search
* Folder contents

A full sample application: localroles form
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A replacement for ``folder_localrole_form`` is included. To use it,
import the CPSDashboards profile and have the CMF action point to
``folder_localroles.html`` in portal_types for Workspaces and Sections.

To add a column to the users search results table, all you need is to add a
widget to the ``localroles_users_row`` layout, refering to the
corresponding field from the members directory schema.

The architecture
----------------

Tabular widgets
~~~~~~~~~~~~~~~

The page rendering uses two layouts. The fist is the one that's been
called. It contains filter widgets to express search criteria and the
main ingredient of the system: the **tabular widget**. The latter performs
the appropriate search and uses the second layout as a renderer for
each row of the result table. Each widget from this layout is
responsible for a column in the table.

There are 3 types of tabular widget, according to the type of item
lookup to perform:

* Folder Contents Widget: filter among childs of a given folder.
* Catalog Tabular Widget: performs a catalog query. A Lucene
  conterpart if provided to leverage Lucene add-ons (query-time batching)
* Directory Search Tabular Widget: that's the one used on the Local
  Roles form


See tabular_widget.txt, catalog.txt, folder_contents.txt and
dirsearch.txt in doc/developer for developer documentation and tests.

Filter widgets
~~~~~~~~~~~~~~

You'll need specific widgets to put along the tabular
widget and welcome the user's search criteria. Several of these **filter
widgets** are provided.

For specific documentation, see doc/developer/filter_widgets.txt

Row widgets
~~~~~~~~~~~

Although any kind of widget can be used in the row layout, a few
specifically designed are also included. For instance, the Type Icon
Widget renders a document's portal_type by its icon, the Qualified
Link Widget is handy to make a link of the document's title, etc.

More documentation can be found in doc/developer/row_widgets.txt and
concrete applications in CPSCourrier

A Base view class
~~~~~~~~~~~~~~~~~

Tabular widget can be used directly in a portlet (as the porlet
widget) or in a document. For views that don't rely on persistent
data, like the advanced search view, we provide a base clas that
manages common needs, for instance managing their rendering modes
(search criteria inputs vs. rendering of results).

This is intended to be plugged in via the Zope3/Five machinery. The
provided local roles form is an example. Other examples can be found
in CPSCourrier.

See doc/developer/views.txt for more details on this.

.. Emacs
.. Local Variables:
.. mode: rst
.. End:
.. Vim
.. vim: set filetype=rst:


