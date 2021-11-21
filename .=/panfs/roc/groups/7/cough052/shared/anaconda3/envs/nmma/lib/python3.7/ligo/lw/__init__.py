# Copyright (C) 2006,2007,2009,2011,2013,2016,2017  Kipp Cannon
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

"""
DOM-like library for handling LIGO Light Weight XML files.  For more
information on the Python DOM specification and SAX document content
handlers, please refer to the Python standard library reference and the
documentation it links to.

Here is a brief tutorial for a common use case:  load a LIGO Light-Weight
XML document containing tabular data complying with the LSC table
definitions, access rows in the tables including the use of ID-based cross
references, modify the contents of a table, and finally write the document
back to disk.  Please see the documentation for the modules, classes,
functions, and methods shown below for more information.

Example:

>>> # import modules
>>> from ligo.lw import ligolw
>>> from ligo.lw import lsctables
>>> from ligo.lw import utils as ligolw_utils
>>>
>>> # define a content handler
>>> class LIGOLWContentHandler(ligolw.LIGOLWContentHandler):
... 	pass
...
>>> lsctables.use_in(LIGOLWContentHandler)
>>>
>>> # load a document.  gzip'ed files are auto-detected
>>> filename = "demo.xml.gz"
>>> xmldoc = ligolw_utils.load_filename(filename, contenthandler = LIGOLWContentHandler, verbose = True)
>>> 
>>> # retrieve the process and sngl_inspiral tables.  these are list-like
>>> # objects of rows.  the row objects' attributes are the column names
>>> process_table = lsctables.ProcessTable.get_table(xmldoc)
>>> sngl_inspiral_table = lsctables.SnglInspiralTable.get_table(xmldoc)
>>> 
>>> # fix the mtotal column in the sngl_inspiral table
>>> for row in sngl_inspiral_table:
...	row.mtotal = row.mass1 + row.mass2
...
>>> # construct a look-up table mapping process_id to row in process table
>>> index = dict((row.process_id, row) for row in process_table)
>>> 
>>> # for each trigger in the sngl_inspiral table, print the name of the user
>>> # who ran the job that produced it, the computer on which the job ran, and
>>> # the GPS end time of the trigger
>>> for row in sngl_inspiral_table:
...	process = index[row.process_id]
...	print "%s@%s: %s s" % (process.username, process.node, str(row.end))
...
>>> # write document.  must explicitly state whether or not the file is to be
>>> # gzip compressed
>>> ligolw_utils.write_filename(xmldoc, filename, compress = 'gz' if filename.endswith(".gz") else False, verbose = True)
"""


__author__ = "Kipp Cannon <kipp.cannon@ligo.org>"
__version__ = "1.7.1"
__date__ = "2021-02-16"


__all__ = [
	"__author__",
	"__date__",
	"__version__",
	"array",
	"ilwd",
	"ligolw",
	"lsctables",
	"param",
	"table",
	"types",
	"utils"
]
