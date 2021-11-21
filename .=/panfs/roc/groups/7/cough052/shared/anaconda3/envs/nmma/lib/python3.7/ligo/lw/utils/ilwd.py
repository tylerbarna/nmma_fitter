# Copyright (C) 2017--2020  Kipp Cannon
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


#
# =============================================================================
#
#                                   Preamble
#
# =============================================================================
#


import logging
from .. import __author__, __date__, __version__
from .. import ligolw
from .. import lsctables
from .. import table as ligolw_table


#
# =============================================================================
#
#                                     Main
#
# =============================================================================
#


def strip_ilwdchar(xmldoc):
	"""
	Transforms a document containing tabular data using ilwd:char style
	row IDs to plain integer row IDs.  This is used to translate
	documents in the older format for compatibility with the modern
	version of the LIGO Light Weight XML Python library.

	NOTE:  the transformation is lossy, and can only be inverted with
	specific knowledge of the structure of the document being
	processed.  Therefore, there is no general implementation of the
	reverse transformation.  Applications that require the inverse
	transformation must implement their own algorithm for doing so,
	specifically for their needs.
	"""
	for table in xmldoc.getElementsByTagName(ligolw.Table.tagName):
		logging.info("table %s:" % table.Name)
		# first strip table names from column names that shouldn't
		# have them
		if table.Name in lsctables.TableByName:
			validcolumns = lsctables.TableByName[table.Name].validcolumns
			stripped_column_to_valid_column = dict((ligolw_table.Column.ColumnName(name), name) for name in validcolumns)
			for column in table.getElementsByTagName(ligolw.Column.tagName):
				if column.getAttribute("Name") not in validcolumns:
					before = column.getAttribute("Name")
					column.setAttribute("Name", stripped_column_to_valid_column[column.Name])
					logging.info("renamed %s column %s to %s" % (table.Name, before, column.getAttribute("Name")))

		# convert ilwd:char IDs to integers
		idattrs = tuple(table.columnnames[i] for i, coltype in enumerate(table.columntypes) if coltype == u"ilwd:char")
		if not idattrs:
			logging.info("no ID columns to convert")
			continue
		logging.info("converting ID column(s) %s" % ", ".join(sorted(idattrs)))
		for row in table:
			for attr in idattrs:
				new_value = getattr(row, attr)
				if new_value is not None:
					setattr(row, attr, int(new_value))

		# update the column types
		for attr in idattrs:
			table.getColumnByName(attr).Type = u"int_8s"

	return xmldoc
