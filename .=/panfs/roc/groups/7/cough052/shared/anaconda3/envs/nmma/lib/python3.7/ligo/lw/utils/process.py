# Copyright (C) 2006--2013,2015,2017,2019,2020  Kipp Cannon
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
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
A collection of utilities to assist applications in manipulating the
process and process_params tables in LIGO Light-Weight XML documents.
"""


from .. import __author__, __date__, __version__
from .. import lsctables


#
# =============================================================================
#
#                               Process Metadata
#
# =============================================================================
#


def set_process_end_time(process):
	"""
	Deprecated.  Use .set_end_time_now() method of the Process object.
	"""
	# FIXME:  delete when nothing needs this.
	process.set_end_time_now()
	return process


def get_process_params(xmldoc, program, param, require_unique_program = True):
	"""
	Return a list of the values stored in the process_params table for
	params named param for the program(s) named program.  The values
	are returned as Python native types, not as the strings appearing
	in the XML document.  If require_unique_program is True (default),
	then the document must contain exactly one program with the
	requested name, otherwise ValueError is raised.  If
	require_unique_program is not True, then there must be at least one
	program with the requested name otherwise ValueError is raised.
	"""
	process_ids = lsctables.ProcessTable.get_table(xmldoc).get_ids_by_program(program)
	if len(process_ids) < 1:
		raise ValueError("process table must contain at least one program named '%s'" % program)
	elif require_unique_program and len(process_ids) != 1:
		raise ValueError("process table must contain exactly one program named '%s'" % program)
	return [row.pyvalue for row in lsctables.ProcessParamsTable.get_table(xmldoc) if (row.process_id in process_ids) and (row.param == param)]


def doc_includes_process(xmldoc, program):
	"""
	Return True if the process table in xmldoc includes entries for a
	program named program.
	"""
	return program in lsctables.ProcessTable.get_table(xmldoc).getColumnByName(u"program")


def register_to_xmldoc(xmldoc, program, paramdict, **kwargs):
	"""
	Ensure the document has sensible process and process_params tables,
	synchronize the process table's ID generator, add a new row to the
	table for the current process, and add rows to the process_params
	table describing the options in paramdict.  program is the name of
	the program.  paramdict is expected to be the .__dict__ contents of
	an optparse.OptionParser options object, or the equivalent.  Any
	keyword arguments are passed to lsctables.Process.initialized(),
	see that method for more information.  The new process row object
	is returned.

	Example

	>>> from ligo.lw import ligolw
	>>> xmldoc = ligolw.Document()
	>>> xmldoc.appendChild(ligolw.LIGO_LW())	# doctest: +ELLIPSIS
	<ligo.lw.ligolw.LIGO_LW object at ...>
	>>> process = register_to_xmldoc(xmldoc, "program_name", {"verbose": True})
	"""
	try:
		proctable = lsctables.ProcessTable.get_table(xmldoc)
	except ValueError:
		proctable = lsctables.New(lsctables.ProcessTable)
		xmldoc.childNodes[0].appendChild(proctable)

	proctable.sync_next_id()
	process = proctable.RowType.initialized(program = program, process_id = proctable.get_next_id(), **kwargs)
	proctable.append(process)

	try:
		paramtable = lsctables.ProcessParamsTable.get_table(xmldoc)
	except ValueError:
		paramtable = lsctables.New(lsctables.ProcessParamsTable)
		xmldoc.childNodes[0].appendChild(paramtable)

	for name, values in paramdict.items():
		# change the name back to the form it had on the command
		# line
		name = u"--%s" % name.replace("_", "-")

		# skip options that aren't set;  ensure values is something
		# that can be iterated over even if there is only one value
		if values is None:
			continue
		elif values is True or values is False:
			# boolen options have no value recorded
			values = [None]
		elif not isinstance(values, list):
			values = [values]

		for value in values:
			paramtable.append(paramtable.RowType(
				program = process.program,
				process_id = process.process_id,
				param = name,
				pyvalue = value
			))
	return process
