# Copyright (C) 2006--2019  Kipp Cannon
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
LSC Table definitions.

See the LDAS CVS repository at
http://www.ldas-sw.ligo.caltech.edu/cgi-bin/cvsweb.cgi/ldas/dbms/db2/sql
for more information.


Customization
-------------

In some cases, applications will need to define sub-classes of the table
and row classes found here or will need to define their own custom tables
altogether.  Once the custom classes are defined, the following steps are
required to incorporate them into this module's document handling
machinery.

Firstly, if a new Table class is defined, the TableByName mapping defined
in this module should be updated.  The TableByName mapping is used to map
table names to corresponding Python classes.  This mapping is used when
parsing XML documents, when extracting the contents of SQL databases and
any other place the conversion from a name to a class definition is
required.  Once the mapping is updated, XML documents containing Table
elements whose names match the custom definition will be converted to
instances of that class (Tables whose names are not recognized are loaded
as instances of the generic ligo.lw.Table class).

Example:

>>> class MyCustomTable(table.Table):
...	tableName = "custom"
...
>>> TableByName[MyCustomTable.tableName] = MyCustomTable

The row type to be used with a table is selected using the .RowType
attribute of the corresponding Table class.  When parsing an XML document
the text is converted into row objects, each of which is created by calling
the .RowType attribute with no arguments.

Example:

>>> class MyCustomTableRow(table.Table.RowType):
...	pass
...
>>> MyCustomTable.RowType = MyCustomTableRow
"""


import functools
import itertools
import math
import numpy
import operator
import os
import socket
import time
import warnings
from xml import sax


from ligo import segments
import lal
from lal import LIGOTimeGPS
from . import __author__, __date__, __version__
from . import ligolw
from . import table
from . import types as ligolwtypes


#
# =============================================================================
#
#                            Convenience Functions
#
# =============================================================================
#


def New(cls, columns = None, **kwargs):
	"""
	Construct a pre-defined LSC table.  The optional columns argument
	is a sequence of the names of the columns the table is to be
	constructed with.  If columns = None, then the table is constructed
	with all valid columns (use columns = [] to create a table with no
	columns).

	Example:

	>>> import sys
	>>> tbl = New(ProcessTable, [u"process_id", u"start_time", u"end_time", u"comment"])
	>>> tbl.write(sys.stdout)	# doctest: +NORMALIZE_WHITESPACE
	<Table Name="process:table">
		<Column Name="process_id" Type="int_8s"/>
		<Column Name="start_time" Type="int_4s"/>
		<Column Name="end_time" Type="int_4s"/>
		<Column Name="comment" Type="lstring"/>
		<Stream Name="process:table" Delimiter="," Type="Local">
		</Stream>
	</Table>
	"""
	new = cls(sax.xmlreader.AttributesImpl({u"Name": cls.TableName.enc(cls.tableName)}), **kwargs)
	for name in columns if columns is not None else sorted(new.validcolumns):
		new.appendColumn(name)
	new._end_of_columns()
	new.appendChild(table.TableStream(sax.xmlreader.AttributesImpl({u"Name": new.getAttribute(u"Name"), u"Delimiter": table.TableStream.Delimiter.default, u"Type": table.TableStream.Type.default})))
	return new


def HasNonLSCTables(elem):
	"""
	Return True if the document tree below elem contains non-LSC
	tables, otherwise return False.
	"""
	return any(t.Name not in TableByName for t in elem.getElementsByTagName(ligolw.Table.tagName))


class instrumentsproperty(object):
	def __init__(self, name):
		self.name = name

	@staticmethod
	def get(ifos):
		"""
		Parse the values stored in the "ifos" and "instruments"
		columns found in many tables.  This function is mostly for
		internal use by the .instruments properties of the
		corresponding row classes.  The mapping from input to
		output is as follows (rules are applied in order):

		input is None --> output is None

		input contains "," --> output is set of strings split on
		"," with leading and trailing whitespace stripped from each
		piece and empty strings removed from the set

		input contains "+" --> output is set of strings split on
		"+" with leading and trailing whitespace stripped from each
		piece and empty strings removed from the set

		else, after stripping input of leading and trailing
		whitespace,

		input has an even length greater than two --> output is set
		of two-character pieces

		input is a non-empty string --> output is a set containing
		input as single value

		else output is an empty set.

		NOTE:  the complexity of this algorithm is a consequence of
		there being several conventions in use for encoding a set
		of instruments into one of these columns;  it has been
		proposed that L.L.W.  documents standardize on the
		comma-delimited variant of the encodings recognized by this
		function, and for this reason the inverse function,
		instrumentsproperty.set(), implements that encoding only.

		NOTE:  to force a string containing an even number of
		characters to be interpreted as a single instrument name
		and not to be be split into two-character pieces, add a ","
		character to the end to force the comma-delimited decoding
		to be used.  instrumentsproperty.set() does this for you.

		Example:

		>>> print(instrumentsproperty.get(None))
		None
		>>> assert instrumentsproperty.get(u"") == set([])
		>>> assert instrumentsproperty.get(u"  ,  ,,") == set([])
		>>> assert instrumentsproperty.get(u"H1") == set([u'H1'])
		>>> assert instrumentsproperty.get(u"SWIFT") == set([u'SWIFT'])
		>>> assert instrumentsproperty.get(u"H1L1") == set([u'H1', u'L1'])
		>>> assert instrumentsproperty.get(u"H1L1,") == set([u'H1L1'])
		>>> assert instrumentsproperty.get(u"H1,L1") == set([u'H1', u'L1'])
		>>> assert instrumentsproperty.get(u"H1+L1") == set([u'H1', u'L1'])
		"""
		if ifos is None:
			return None
		if u"," in ifos:
			result = set(ifo.strip() for ifo in ifos.split(u","))
			result.discard(u"")
			return result
		if u"+" in ifos:
			result = set(ifo.strip() for ifo in ifos.split(u"+"))
			result.discard(u"")
			return result
		ifos = ifos.strip()
		if len(ifos) > 2 and not len(ifos) % 2:
			# if ifos is a string with an even number of
			# characters greater than two, split it into
			# two-character pieces.  FIXME:  remove this when
			# the inspiral codes don't write ifos strings like
			# this anymore
			return set(ifos[n:n+2] for n in range(0, len(ifos), 2))
		if ifos:
			return set([ifos])
		return set()

	@staticmethod
	def set(instruments):
		"""
		Convert an iterable of instrument names into a value
		suitable for storage in the "ifos" column found in many
		tables.  This function is mostly for internal use by the
		.instruments properties of the corresponding row classes.
		The input can be None or an iterable of zero or more
		instrument names, none of which may be zero-length, consist
		exclusively of spaces, or contain "," or "+" characters.
		The output is a single string containing the unique
		instrument names concatenated using "," as a delimiter.
		instruments will only be iterated over once and so can be a
		generator expression.  Whitespace is allowed in instrument
		names but might not be preserved.  Repeated names will not
		be preserved.

		NOTE:  in the special case that there is 1 instrument name
		in the iterable and it has an even number of characters > 2
		in it, the output will have a "," appended in order to
		force instrumentsproperty.get() to parse the string back
		into a single instrument name.  This is a special case
		included temporarily to disambiguate the encoding until all
		codes have been ported to the comma-delimited encoding.
		This behaviour will be discontinued at that time.  DO NOT
		WRITE CODE THAT RELIES ON THIS!  You have been warned.

		Example:

		>>> print(instrumentsproperty.set(None))
		None
		>>> assert instrumentsproperty.set(()) == u''
		>>> assert instrumentsproperty.set((u"H1",)) == u'H1'
		>>> assert instrumentsproperty.set((u"H1",u"H1",u"H1")) == u'H1'
		>>> assert instrumentsproperty.set((u"H1",u"L1")) == u'H1,L1'
		>>> assert instrumentsproperty.set((u"SWIFT",)) == u'SWIFT'
		>>> assert instrumentsproperty.set((u"H1L1",)) == u'H1L1,'
		"""
		if instruments is None:
			return None
		_instruments = sorted(set(instrument.strip() for instrument in instruments))
		# safety check:  refuse to accept blank names, or names
		# with commas or pluses in them as they cannot survive the
		# encode/decode process
		if not all(_instruments) or any(u"," in instrument or u"+" in instrument for instrument in _instruments):
			raise ValueError(instruments)
		if len(_instruments) == 1 and len(_instruments[0]) > 2 and not len(_instruments[0]) % 2:
			# special case disambiguation.  FIXME:  remove when
			# everything uses the comma-delimited encoding
			return u"%s," % _instruments[0]
		return u",".join(_instruments)

	def __get__(self, obj, cls = None):
		return self.get(getattr(obj, self.name))

	def __set__(self, obj, instruments):
		setattr(obj, self.name, self.set(instruments))


class gpsproperty(object):
	"""
	Descriptor used internally to implement LIGOTimeGPS-valued
	properties using pairs of integer attributes on row objects, one
	for the integer seconds part of the GPS time and one for the
	integer nanoseconds part.

	Non-LIGOTimeGPS values are converted to LIGOTimeGPS before encoding
	them into the integer attributes.  None is allowed as a special
	case, which is encoded by setting both column attributes to None.

	For the purpose of representing the boundaries of unbounded
	segments (open-ended time intervals), +inf and -inf are also
	allowed, and will be encoded into and decoded out of the integer
	attributes.  To do so, a non-standard encoding is used that makes
	use of denormalized GPS times, that is times whose nanosecond
	component has a magnitude greater than 999999999.  Two such values
	are reserved for +/- infinity.  To guard against the need for
	additional special encodings in the future, this descriptor
	reserves all denormalized values and will not allow calling code to
	set GPS times to those values.  Calling code must provide
	normalized GPS times, times with nanosecond components whose
	magnitudes are not greater than 999999999.  When decoded, the
	values reported are segments.PosInfinity or segments.NegInfinity.
	"""
	def __init__(self, s_name, ns_name):
		self.s_name = s_name
		self.get_s = operator.attrgetter(s_name)
		self.ns_name = ns_name
		self.get_ns = operator.attrgetter(ns_name)

	posinf = 0x7FFFFFFF, 0xFFFFFFFF
	neginf = 0xFFFFFFFF, 0xFFFFFFFF
	infs = posinf, neginf

	def __get__(self, obj, cls = None):
		s = self.get_s(obj)
		ns = self.get_ns(obj)
		if s is None and ns is None:
			return None
		if ns == 0xFFFFFFFF:
			if (s, ns) == self.posinf:
				return segments.PosInfinity
			elif (s, ns) == self.neginf:
				return segments.NegInfinity
			raise ValueError("unrecognized denormalized number LIGOTimeGPS(%d,%d)" % (s, ns))
		return LIGOTimeGPS(s, ns)

	def __set__(self, obj, gps):
		if gps is None:
			s = ns = None
		elif isinstance(gps, segments.infinity) or math.isinf(gps):
			if gps > 0:
				s, ns = self.posinf
			elif gps < 0:
				s, ns = self.neginf
			else:
				raise ValueError(gps)
		else:
			try:
				s = gps.gpsSeconds
				ns = gps.gpsNanoSeconds
			except AttributeError:
				# try converting and going again
				return self.__set__(obj, LIGOTimeGPS(gps))
			if abs(ns) > 999999999:
				raise ValueError("denormalized LIGOTimeGPS not allowed: LIGOTimeGPS(%d, %d)" % (s, ns))
		setattr(obj, self.s_name, s)
		setattr(obj, self.ns_name, ns)


class gpsproperty_with_gmst(gpsproperty):
	"""
	Variant of the gpsproperty descriptor, adding support for a third
	"GMST" column.  When assigning a time to the GPS-valued descriptor,
	after the pair of integer attributes are set to the encoded form of
	the GPS time, the value is retrieved and the GMST column is set to
	the Greenwhich mean sidereal time corresponding to that GPS time.
	Note that the conversion to sidereal time is performed after
	encoding the GPS time into the integer seconds and nanoseconds
	attributes, so the sidereal time will reflect any rounding that has
	occured as a result of that encoding.  If the GPS time is set to
	None or +inf or -inf, the sidereal time is set to that value as
	well.
	"""
	def __init__(self, s_name, ns_name, gmst_name):
		super(gpsproperty_with_gmst, self).__init__(s_name, ns_name)
		self.gmst_name = gmst_name

	def __set__(self, obj, gps):
		super(gpsproperty_with_gmst, self).__set__(obj, gps)
		if gps is None:
			setattr(obj, self.gmst_name, None)
		else:
			# re-retrieve the value in case it required type
			# conversion
			gps = self.__get__(obj)
			if not isinstance(gps, segments.infinity):
				setattr(obj, self.gmst_name, lal.GreenwichMeanSiderealTime(gps))
			elif gps > 0:
				setattr(obj, self.gmst_name, float("+inf"))
			elif gps < 0:
				setattr(obj, self.gmst_name, float("-inf"))
			else:
				# this should be impossible
				raise ValueError(gps)


class segmentproperty(object):
	"""
	Descriptor used internally to expose pairs of GPS-valued properties
	as segment-valued properties.  A segment may be set to None, which
	is encoded by setting both GPS-valued properties to None.  Likewise
	if both GPS-valued properties are set to None then the value
	reported by this descriptor is None, not (None, None).

	See the documentation for gpsproperty for more information on the
	encodings it uses for special values and the limitations they
	create.
	"""
	def __init__(self, start_name, stop_name):
		self.start = start_name
		self.stop = stop_name

	def __get__(self, obj, cls = None):
		start = getattr(obj, self.start)
		stop = getattr(obj, self.stop)
		if start is None and stop is None:
			return None
		return segments.segment(start, stop)

	def __set__(self, obj, seg):
		if seg is None:
			start = stop = None
		else:
			start, stop = seg
		setattr(obj, self.start, start)
		setattr(obj, self.stop, stop)


#
# =============================================================================
#
#                                process:table
#
# =============================================================================
#


ProcessID = table.next_id.type(u"process_id")


class ProcessTable(table.Table):
	tableName = "process"
	validcolumns = {
		"program": "lstring",
		"version": "lstring",
		"cvs_repository": "lstring",
		"cvs_entry_time": "int_4s",
		"comment": "lstring",
		"is_online": "int_4s",
		"node": "lstring",
		"username": "lstring",
		"unix_procid": "int_4s",
		"start_time": "int_4s",
		"end_time": "int_4s",
		"jobid": "int_4s",
		"domain": "lstring",
		"ifos": "lstring",
		"process_id": "int_8s"
	}
	constraints = "PRIMARY KEY (process_id)"
	next_id = ProcessID(0)

	def get_ids_by_program(self, program):
		"""
		Return a set containing the process IDs from rows whose
		program string equals the given program.
		"""
		return set(row.process_id for row in self if row.program == program)

	@staticmethod
	def get_username():
		"""
		Utility to help retrieve a sensible value for the current
		username.  First the environment variable LOGNAME is tried,
		if that is not set the environment variable USERNAME is
		tried, if that is not set the password database is
		consulted (only on Unix systems, if the import of the pwd
		module succeeds), finally if that fails KeyError is raised.
		"""
		try:
			return os.environ["LOGNAME"]
		except KeyError:
			pass
		try:
			return os.environ["USERNAME"]
		except KeyError:
			pass
		try:
			import pwd
			return pwd.getpwuid(os.getuid())[0]
		except (ImportError, KeyError):
			raise KeyError


class Process(table.Table.RowType):
	"""
	Example:

	>>> x = Process()
	>>> x.instruments = (u"H1", u"L1")
	>>> assert x.ifos == u'H1,L1'
	>>> assert x.instruments == set([u'H1', u'L1'])
	>>> # truncates to integers
	>>> x.start = 10.5
	>>> x.start
	LIGOTimeGPS(10, 0)
	>>> x.end = 20.5
	>>> x.end
	LIGOTimeGPS(20, 0)
	>>> x.segment
	segment(LIGOTimeGPS(10, 0), LIGOTimeGPS(20, 0))
	"""
	__slots__ = tuple(map(table.Column.ColumnName, ProcessTable.validcolumns))

	@property
	def start_time_ns(eslf):
		return 0
	@start_time_ns.setter
	def start_time_ns(self, val):
		pass

	@property
	def end_time_ns(eslf):
		return 0
	@end_time_ns.setter
	def end_time_ns(self, val):
		pass

	instruments = instrumentsproperty("ifos")
	start = gpsproperty("start_time", "start_time_ns")
	end = gpsproperty("end_time", "end_time_ns")
	segment = segmentproperty("start", "end")

	@classmethod
	def initialized(cls, program = None, version = None, cvs_repository = None, cvs_entry_time = None, comment = None, is_online = False, jobid = 0, domain = None, instruments = None, process_id = None):
		"""
		Create a new Process object and initialize its attributes
		to sensible defaults.  If not None, program, version,
		cvs_repository, comment, and domain should all be strings
		or unicodes.  If cvs_entry_time is not None, it must be a
		string or unicode in the format "YYYY-MM-DD HH:MM:SS".
		is_online should be boolean, jobid an integer.  If not
		None, instruments must be an iterable (set, tuple, etc.) of
		instrument names (strings or unicodes).

		In addition, .node is set to the current hostname,
		.unix_procid is set to the current process ID, .username is
		set to the current user's name, .start_time is set to the
		current GPS time.

		Note:  if the process_id keyword argument is None (the
		default), then the process_id attribute is not set, it is
		left uninitialized rather than setting it to None.  It must
		be initialized before the row object can be written to a
		file, and so in this way the calling code is required to
		provide a proper value for it.

		Example:

		>>> process = Process.initialized()
		"""
		self = cls(
			program = program,
			version = version,
			cvs_repository = cvs_repository,
			cvs_entry_time = lal.UTCToGPS(time.strptime(cvs_entry_time, "%Y-%m-%d %H:%M:%S +0000")) if cvs_entry_time is not None else None,
			comment = comment,
			is_online = int(is_online),
			node = socket.gethostname(),
			unix_procid = os.getpid(),
			start_time = lal.UTCToGPS(time.gmtime()),
			end_time = None,
			jobid = jobid,
			domain = domain,
			instruments = instruments
		)
		try:
			self.username = ProcessTable.get_username()
		except KeyError:
			self.username = None
		if process_id is not None:
			self.process_id = process_id
		return self

	def set_end_time_now(self):
		"""
		Set .end_time to the current GPS time.
		"""
		self.end_time = lal.UTCToGPS(time.gmtime())


ProcessTable.RowType = Process


#
# =============================================================================
#
#                             process_params:table
#
# =============================================================================
#


class ProcessParamsTable(table.Table):
	tableName = "process_params"
	validcolumns = {
		"program": "lstring",
		"process:process_id": "int_8s",
		"param": "lstring",
		"type": "lstring",
		"value": "lstring"
	}
	# FIXME: these constraints break ID remapping in the DB backend.
	# an index is used instead.  switch back to the constraints when I
	# can figure out how not to break remapping.
	#constraints = "PRIMARY KEY (process_id, param)"
	how_to_index = {
		"pp_pip_index": ("process_id", "param"),
	}

	def append(self, row):
		if row.type is not None and row.type not in ligolwtypes.Types:
			raise ligolw.ElementError("unrecognized type '%s' for process %d param '%s'" % (row.type, row.process_id, row.param))
		super(ProcessParamsTable, self).append(row)


class ProcessParams(table.Table.RowType):
	"""
	Example:

	>>> x = ProcessParams()
	>>> x.pyvalue = u"test"
	>>> print(x.type)
	lstring
	>>> print(x.value)
	test
	>>> print(x.pyvalue)
	test
	>>> x.pyvalue = 6.
	>>> print(x.type)
	real_8
	>>> assert x.value == u'6'
	>>> print(x.pyvalue)
	6.0
	>>> x.pyvalue = None
	>>> print(x.type)
	None
	>>> print(x.value)
	None
	>>> print(x.pyvalue)
	None
	>>> x.pyvalue = True
	>>> print(x.type)
	int_4s
	>>> assert x.value == u'1'
	>>> x.pyvalue
	1
	"""
	__slots__ = tuple(map(table.Column.ColumnName, ProcessParamsTable.validcolumns))

	@property
	def pyvalue(self):
		if self.value is None:
			return None
		try:
			parsefunc = ligolwtypes.ToPyType[self.type]
		except KeyError:
			raise ValueError("invalid type '%s'" % self.type)
		return parsefunc(self.value)

	@pyvalue.setter
	def pyvalue(self, value):
		if value is None:
			self.type = self.value = None
		else:
			try:
				self.type = ligolwtypes.FromPyType[type(value)]
			except KeyError:
				raise ValueError("type not supported: %s" % repr(type(value)))
			self.value = value if self.type in ligolwtypes.StringTypes else ligolwtypes.FormatFunc[self.type](value)


ProcessParamsTable.RowType = ProcessParams


#
# =============================================================================
#
#                             search_summary:table
#
# =============================================================================
#


class SearchSummaryTable(table.Table):
	tableName = "search_summary"
	validcolumns = {
		"process:process_id": "int_8s",
		"shared_object": "lstring",
		"lalwrapper_cvs_tag": "lstring",
		"lal_cvs_tag": "lstring",
		"comment": "lstring",
		"ifos": "lstring",
		"in_start_time": "int_4s",
		"in_start_time_ns": "int_4s",
		"in_end_time": "int_4s",
		"in_end_time_ns": "int_4s",
		"out_start_time": "int_4s",
		"out_start_time_ns": "int_4s",
		"out_end_time": "int_4s",
		"out_end_time_ns": "int_4s",
		"nevents": "int_4s",
		"nnodes": "int_4s"
	}
	how_to_index = {
		"ss_pi_index": ("process_id",),
	}

	def get_in_segmentlistdict(self, process_ids = None):
		"""
		Return a segmentlistdict mapping instrument to in segment
		list.  If process_ids is a sequence of process IDs, then
		only rows with matching IDs are included otherwise all rows
		are included.

		Note:  the result is not coalesced, each segmentlist
		contains the segments listed for that instrument as they
		appeared in the table.
		"""
		seglists = segments.segmentlistdict()
		for row in self:
			ifos = row.instruments or (None,)
			if process_ids is None or row.process_id in process_ids:
				seglists.extend(dict((ifo, segments.segmentlist([row.in_segment])) for ifo in ifos))
		return seglists

	def get_out_segmentlistdict(self, process_ids = None):
		"""
		Return a segmentlistdict mapping instrument to out segment
		list.  If process_ids is a sequence of process IDs, then
		only rows with matching IDs are included otherwise all rows
		are included.

		Note:  the result is not coalesced, each segmentlist
		contains the segments listed for that instrument as they
		appeared in the table.
		"""
		seglists = segments.segmentlistdict()
		for row in self:
			ifos = row.instruments or (None,)
			if process_ids is None or row.process_id in process_ids:
				seglists.extend(dict((ifo, segments.segmentlist([row.out_segment])) for ifo in ifos))
		return seglists


class SearchSummary(table.Table.RowType):
	"""
	Example:

	>>> x = SearchSummary()
	>>> x.instruments = (u"H1", u"L1")
	>>> print(x.ifos)
	H1,L1
	>>> assert x.instruments == set([u'H1', u'L1'])
	>>> x.in_start = x.out_start = LIGOTimeGPS(0)
	>>> x.in_end = x.out_end = LIGOTimeGPS(10)
	>>> x.in_segment
	segment(LIGOTimeGPS(0, 0), LIGOTimeGPS(10, 0))
	>>> x.out_segment
	segment(LIGOTimeGPS(0, 0), LIGOTimeGPS(10, 0))
	>>> x.in_segment = x.out_segment = None
	>>> print(x.in_segment)
	None
	>>> print(x.out_segment)
	None
	"""
	__slots__ = tuple(map(table.Column.ColumnName, SearchSummaryTable.validcolumns))

	instruments = instrumentsproperty("ifos")

	in_start = gpsproperty("in_start_time", "in_start_time_ns")
	in_end = gpsproperty("in_end_time", "in_end_time_ns")
	out_start = gpsproperty("out_start_time", "out_start_time_ns")
	out_end = gpsproperty("out_end_time", "out_end_time_ns")

	in_segment = segmentproperty("in_start", "in_end")
	out_segment = segmentproperty("out_start", "out_end")

	@classmethod
	def initialized(cls, process, shared_object = "standalone", lalwrapper_cvs_tag = "", lal_cvs_tag = "", comment = None, ifos = None, inseg = None, outseg = None, nevents = 0, nnodes = 1):
		"""
		Create and return a sensibly initialized row for the
		search_summary table.  process is an initialized row for
		the process table.
		"""
		return cls(
			process_id = process.process_id,
			shared_object = shared_object,
			lalwrapper_cvs_tag = lalwrapper_cvs_tag,
			lal_cvs_tag = lal_cvs_tag,
			comment = comment or process.comment,
			instruments = ifos if ifos is not None else process.instruments,
			in_segment = inseg,
			out_segment = outseg,
			nevents = nevents,
			nnodes = nnodes
		)


SearchSummaryTable.RowType = SearchSummary


#
# =============================================================================
#
#                            search_summvars:table
#
# =============================================================================
#


SearchSummVarsID = table.next_id.type(u"search_summvar_id")


class SearchSummVarsTable(table.Table):
	tableName = "search_summvars"
	validcolumns = {
		"process:process_id": "int_8s",
		"search_summvar_id": "int_8s",
		"name": "lstring",
		"string": "lstring",
		"value": "real_8"
	}
	constraints = "PRIMARY KEY (search_summvar_id)"
	next_id = SearchSummVarsID(0)


class SearchSummVars(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, SearchSummVarsTable.validcolumns))


SearchSummVarsTable.RowType = SearchSummVars


#
# =============================================================================
#
#                               sngl_burst:table
#
# =============================================================================
#


SnglBurstID = table.next_id.type(u"event_id")


class SnglBurstTable(table.Table):
	tableName = "sngl_burst"
	validcolumns = {
		"creator_db": "int_4s",
		"process:process_id": "int_8s",
		"filter:filter_id": "int_8s",
		"ifo": "lstring",
		"search": "lstring",
		"channel": "lstring",
		"start_time": "int_4s",
		"start_time_ns": "int_4s",
		"stop_time": "int_4s",
		"stop_time_ns": "int_4s",
		"duration": "real_4",
		"flow": "real_4",
		"fhigh": "real_4",
		"central_freq": "real_4",
		"bandwidth": "real_4",
		"amplitude": "real_4",
		"snr": "real_4",
		"confidence": "real_4",
		"chisq": "real_8",
		"chisq_dof": "real_8",
		"tfvolume": "real_4",
		"hrss": "real_4",
		"time_lag": "real_4",
		"peak_time": "int_4s",
		"peak_time_ns": "int_4s",
		"peak_frequency": "real_4",
		"peak_strain": "real_4",
		"peak_time_error": "real_4",
		"peak_frequency_error": "real_4",
		"peak_strain_error": "real_4",
		"ms_start_time": "int_4s",
		"ms_start_time_ns": "int_4s",
		"ms_stop_time": "int_4s",
		"ms_stop_time_ns": "int_4s",
		"ms_duration": "real_4",
		"ms_flow": "real_4",
		"ms_fhigh": "real_4",
		"ms_bandwidth": "real_4",
		"ms_hrss": "real_4",
		"ms_snr": "real_4",
		"ms_confidence": "real_4",
		"param_one_name": "lstring",
		"param_one_value": "real_8",
		"param_two_name": "lstring",
		"param_two_value": "real_8",
		"param_three_name": "lstring",
		"param_three_value": "real_8",
		"event_id": "int_8s"
	}
	constraints = "PRIMARY KEY (event_id)"
	next_id = SnglBurstID(0)


class SnglBurst(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, SnglBurstTable.validcolumns))

	#
	# Tile properties
	#

	start = gpsproperty("start_time", "start_time_ns")
	stop = gpsproperty("stop_time", "stop_time_ns")
	peak = gpsproperty("peak_time", "peak_time_ns")

	@property
	def period(self):
		start = self.start
		try:
			stop = self.stop
		except AttributeError:
			stop = None
		# special case:  use duration if stop is not recorded
		if start is not None and stop is None and self.duration is not None:
			stop = start + self.duration
		if start is None and stop is None:
			return None
		return segments.segment(start, stop)

	@period.setter
	def period(self, seg):
		if seg is None:
			self.start = self.stop = self.duration = None
		else:
			self.start, self.stop = seg
			self.duration = float(abs(seg))

	@property
	def band(self):
		if self.central_freq is None and self.bandwidth is None:
			return None
		return segments.segment(self.central_freq - self.bandwidth / 2., self.central_freq + self.bandwidth / 2.)

	@band.setter
	def band(self, seg):
		if seg is None:
			try:
				self.flow = self.fhigh = None
			except AttributeError:
				# not in LAL C version
				pass
			self.central_freq = self.bandwidth = None
		else:
			try:
				self.flow, self.fhigh = seg
			except AttributeError:
				# not in LAL C version
				pass
			self.central_freq = sum(seg) / 2.
			self.bandwidth = abs(seg)

	#
	# "Most significant pixel" properties
	#

	ms_start = gpsproperty("ms_start_time", "ms_start_time_ns")
	ms_stop = gpsproperty("ms_stop_time", "ms_stop_time_ns")
	ms_peak = gpsproperty("ms_peak_time", "ms_peak_time_ns")

	@property
	def ms_period(self):
		start = self.ms_start
		stop = self.ms_stop
		# special case:  use duration if stop is not recorded
		if start is not None and stop is None and self.ms-duration is not None:
			stop = start + self.ms_duration
		if start is None and stop is None:
			return None
		return segments.segment(start, stop)

	@ms_period.setter
	def ms_period(self, seg):
		if seg is None:
			self.ms_start = self.ms_stop = self.ms_duration = None
		else:
			self.ms_start, self.ms_stop = seg
			self.ms_duration = float(abs(seg))

	@property
	def ms_band(self):
		if self.ms_flow is None and self.ms_bandwidth is None:
			return None
		return segments.segment(self.ms_flow, self.ms_flow + self.ms_bandwidth)

	@ms_band.setter
	def ms_band(self, seg):
		if seg is None:
			self.ms_bandwidth = self.ms_flow = self.ms_fhigh = None
		else:
			self.ms_flow, self.ms_fhigh = seg
			self.ms_bandwidth = abs(seg)


SnglBurstTable.RowType = SnglBurst


#
# =============================================================================
#
#                             sngl_inspiral:table
#
# =============================================================================
#


SnglInspiralID = table.next_id.type(u"event_id")


class SnglInspiralTable(table.Table):
	tableName = "sngl_inspiral"
	validcolumns = {
		"process:process_id": "int_8s",
		"ifo": "lstring",
		"search": "lstring",
		"channel": "lstring",
		"end_time": "int_4s",
		"end_time_ns": "int_4s",
		"end_time_gmst": "real_8",
		"impulse_time": "int_4s",
		"impulse_time_ns": "int_4s",
		"template_duration": "real_8",
		"event_duration": "real_8",
		"amplitude": "real_4",
		"eff_distance": "real_4",
		"coa_phase": "real_4",
		"mass1": "real_4",
		"mass2": "real_4",
		"mchirp": "real_4",
		"mtotal": "real_4",
		"eta": "real_4",
		"kappa": "real_4",
		"chi": "real_4",
		"tau0": "real_4",
		"tau2": "real_4",
		"tau3": "real_4",
		"tau4": "real_4",
		"tau5": "real_4",
		"ttotal": "real_4",
		"psi0": "real_4",
		"psi3": "real_4",
		"alpha": "real_4",
		"alpha1": "real_4",
		"alpha2": "real_4",
		"alpha3": "real_4",
		"alpha4": "real_4",
		"alpha5": "real_4",
		"alpha6": "real_4",
		"beta": "real_4",
		"f_final": "real_4",
		"snr": "real_4",
		"chisq": "real_4",
		"chisq_dof": "int_4s",
		"bank_chisq": "real_4",
		"bank_chisq_dof": "int_4s",
		"cont_chisq": "real_4",
		"cont_chisq_dof": "int_4s",
		"sigmasq": "real_8",
		"rsqveto_duration": "real_4",
		"Gamma0": "real_4",
		"Gamma1": "real_4",
		"Gamma2": "real_4",
		"Gamma3": "real_4",
		"Gamma4": "real_4",
		"Gamma5": "real_4",
		"Gamma6": "real_4",
		"Gamma7": "real_4",
		"Gamma8": "real_4",
		"Gamma9": "real_4",
		"spin1x": "real_4",
		"spin1y": "real_4",
		"spin1z": "real_4",
		"spin2x": "real_4",
		"spin2y": "real_4",
		"spin2z": "real_4",
		"event_id": "int_8s"
	}
	constraints = "PRIMARY KEY (event_id)"
	next_id = SnglInspiralID(0)


class SnglInspiral(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, SnglInspiralTable.validcolumns))

	@staticmethod
	def chirp_distance(dist, mchirp, ref_mass=1.4):
		return dist * (2.**(-1./5) * ref_mass / mchirp)**(5./6)

	#
	# Properties
	#

	end = gpsproperty_with_gmst("end_time", "end_time_ns", "end_time_gmst")

	@property
	def spin1(self):
		if self.spin1x is None and self.spin1y is None and self.spin1z is None:
			return None
		return numpy.array((self.spin1x, self.spin1y, self.spin1z), dtype = "double")

	@spin1.setter
	def spin1(self, spin):
		if spin is None:
			self.spin1x = self.spin1y = self.spin1z = None
		else:
			self.spin1x, self.spin1y, self.spin1z = spin

	@property
	def spin2(self):
		if self.spin2x is None and self.spin2y is None and self.spin2z is None:
			return None
		return numpy.array((self.spin2x, self.spin2y, self.spin2z), dtype = "double")

	@spin2.setter
	def spin2(self, spin):
		if spin is None:
			self.spin2x = self.spin2y = self.spin2z = None
		else:
			self.spin2x, self.spin2y, self.spin2z = spin

	#
	# simulate tempate_id column
	# FIXME:  add a proper column for this
	#

	@property
	def template_id(self):
		return int(self.Gamma0)

	@template_id.setter
	def template_id(self, template_id):
		self.Gamma0 = float(template_id)

	#
	# Methods
	#

	# FIXME: how are two inspiral events defined to be the same?
	def __eq__(self, other):
		return self.ifo == other.ifo and self.end == other.end and self.mass1 == other.mass1 and self.mass2 == other.mass2 and self.spin1 == other.spin1 and self.spin2 == other.spin2 and self.search == other.search


SnglInspiralTable.RowType = SnglInspiral


#
# =============================================================================
#
#                             coinc_inspiral:table
#
# =============================================================================
#


class CoincInspiralTable(table.Table):
	tableName = "coinc_inspiral"
	validcolumns = {
		"coinc_event:coinc_event_id": "int_8s",
		"ifos": "lstring",
		"end_time": "int_4s",
		"end_time_ns": "int_4s",
		"mass": "real_8",
		"mchirp": "real_8",
		"minimum_duration": "real_8",
		"snr": "real_8",
		"false_alarm_rate": "real_8",
		"combined_far": "real_8"
	}
	# FIXME:  like some other tables here, this table should have the
	# constraint that the coinc_event_id column is a primary key.  this
	# breaks ID reassignment in ligolw_sqlite, so until that is fixed
	# the constraint is being replaced with an index.
	#constraints = "PRIMARY KEY (coinc_event_id)"
	how_to_index = {
		"ci_cei_index": ("coinc_event_id",)
	}


class CoincInspiral(table.Table.RowType):
	"""
	Example:

	>>> x = CoincInspiral()
	>>> x.instruments = (u"H1", u"L1")
	>>> print(x.ifos)
	H1,L1
	>>> assert x.instruments == set([u'H1', u'L1'])
	>>> x.end = LIGOTimeGPS(10)
	>>> x.end
	LIGOTimeGPS(10, 0)
	>>> x.end = None
	>>> print(x.end)
	None
	"""
	__slots__ = tuple(map(table.Column.ColumnName, CoincInspiralTable.validcolumns))

	instruments = instrumentsproperty("ifos")

	end = gpsproperty("end_time", "end_time_ns")


CoincInspiralTable.RowType = CoincInspiral


#
# =============================================================================
#
#                             sngl_ringdown:table
#
# =============================================================================
#


SnglRingdownID = table.next_id.type(u"event_id")


class SnglRingdownTable(table.Table):
	tableName = "sngl_ringdown"
	validcolumns = {
		"process:process_id": "int_8s",
		"ifo": "lstring",
		"channel": "lstring",
		"start_time": "int_4s",
		"start_time_ns": "int_4s",
		"start_time_gmst": "real_8",
		"frequency": "real_4",
		"quality": "real_4",
		"phase": "real_4",
		"mass": "real_4",
		"spin": "real_4",
		"epsilon": "real_4",
		"num_clust_trigs": "int_4s",
		"ds2_H1H2": "real_4",
		"ds2_H1L1": "real_4",
		"ds2_H1V1": "real_4",
		"ds2_H2L1": "real_4",
		"ds2_H2V1": "real_4",
		"ds2_L1V1": "real_4",
		"amplitude": "real_4",
		"snr": "real_4",
		"eff_dist": "real_4",
		"sigma_sq": "real_8",
		"event_id": "int_8s"
	}
	constraints = "PRIMARY KEY (event_id)"
	next_id = SnglRingdownID(0)


class SnglRingdown(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, SnglRingdownTable.validcolumns))

	start = gpsproperty_with_gmst("start_time", "start_time_ns", "start_time_gmst")


SnglRingdownTable.RowType = SnglRingdown


#
# =============================================================================
#
#                             coinc_ringdown:table
#
# =============================================================================
#


class CoincRingdownTable(table.Table):
	tableName = "coinc_ringdown"
	validcolumns = {
		"coinc_event:coinc_event_id": "int_8s",
		"ifos": "lstring",
		"start_time": "int_4s",
		"start_time_ns": "int_4s",
		"frequency": "real_8",
		"quality": "real_8",
		"mass": "real_8",
		"spin": "real_8",
		"snr": "real_8",
		"choppedl_snr": "real_8",
		"snr_sq": "real_8",
		"eff_coh_snr": "real_8",
		"null_stat": "real_8",
		"kappa": "real_8",
		"snr_ratio": "real_8",
		"false_alarm_rate": "real_8",
		"combined_far": "real_8"
	}
	# constraints = "PRIMARY KEY (coinc_event_id)"
	how_to_index = {
		"cr_cei_index": ("coinc_event_id",)
	}


class CoincRingdown(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, CoincRingdownTable.validcolumns))

	instruments = instrumentsproperty("ifos")

	start = gpsproperty("start_time", "start_time_ns")


CoincRingdownTable.RowType = CoincRingdown


#
# =============================================================================
#
#                              sim_inspiral:table
#
# =============================================================================
#


SimInspiralID = table.next_id.type(u"simulation_id")


class SimInspiralTable(table.Table):
	tableName = "sim_inspiral"
	validcolumns = {
		"process:process_id": "int_8s",
		"waveform": "lstring",
		"geocent_end_time": "int_4s",
		"geocent_end_time_ns": "int_4s",
		"h_end_time": "int_4s",
		"h_end_time_ns": "int_4s",
		"l_end_time": "int_4s",
		"l_end_time_ns": "int_4s",
		"g_end_time": "int_4s",
		"g_end_time_ns": "int_4s",
		"t_end_time": "int_4s",
		"t_end_time_ns": "int_4s",
		"v_end_time": "int_4s",
		"v_end_time_ns": "int_4s",
		"end_time_gmst": "real_8",
		"source": "lstring",
		"mass1": "real_4",
		"mass2": "real_4",
		"mchirp": "real_4",
		"eta": "real_4",
		"distance": "real_4",
		"longitude": "real_4",
		"latitude": "real_4",
		"inclination": "real_4",
		"coa_phase": "real_4",
		"polarization": "real_4",
		"psi0": "real_4",
		"psi3": "real_4",
		"alpha": "real_4",
		"alpha1": "real_4",
		"alpha2": "real_4",
		"alpha3": "real_4",
		"alpha4": "real_4",
		"alpha5": "real_4",
		"alpha6": "real_4",
		"beta": "real_4",
		"spin1x": "real_4",
		"spin1y": "real_4",
		"spin1z": "real_4",
		"spin2x": "real_4",
		"spin2y": "real_4",
		"spin2z": "real_4",
		"theta0": "real_4",
		"phi0": "real_4",
		"f_lower": "real_4",
		"f_final": "real_4",
		"eff_dist_h": "real_4",
		"eff_dist_l": "real_4",
		"eff_dist_g": "real_4",
		"eff_dist_t": "real_4",
		"eff_dist_v": "real_4",
		"numrel_mode_min": "int_4s",
		"numrel_mode_max": "int_4s",
		"numrel_data": "lstring",
		"amp_order": "int_4s",
		"taper": "lstring",
		"bandpass": "int_4s",
		"simulation_id": "int_8s"
	}
	constraints = "PRIMARY KEY (simulation_id)"
	next_id = SimInspiralID(0)


class SimInspiral(table.Table.RowType):
	"""
	Example:

	>>> x = SimInspiral()
	>>> x.ra_dec = 0., 0.
	>>> x.ra_dec
	(0.0, 0.0)
	>>> x.ra_dec = None
	>>> print(x.ra_dec)
	None
	>>> x.time_geocent = None
	>>> print(x.time_geocent)
	None
	>>> print(x.end_time_gmst)
	None
	>>> x.time_geocent = LIGOTimeGPS(6e8)
	>>> print(x.time_geocent)
	600000000
	>>> print(round(x.end_time_gmst, 8))
	-2238.39417156
	>>> x.distance = 100e6
	>>> x.ra_dec = 0., 0.
	>>> x.inclination = 0.
	>>> x.polarization = 0.
	>>> x.snr_geometry_factors(("H1",))
	{'H1': 0.6773046071543202}
	>>> x.effective_distances(("H1",))
	{'H1': 147644056.9630077}
	>>> x.expected_snrs({"H1": 150e6})
	{'H1': 8.127655285851842}
	"""
	__slots__ = tuple(map(table.Column.ColumnName, SimInspiralTable.validcolumns))

	time_geocent = gpsproperty_with_gmst("geocent_end_time", "geocent_end_time_ns", "end_time_gmst")

	@property
	def ra_dec(self):
		if self.longitude is None and self.latitude is None:
			return None
		return self.longitude, self.latitude

	@ra_dec.setter
	def ra_dec(self, radec):
		if radec is None:
			self.longitude = self.latitude = None
		else:
			self.longitude, self.latitude = radec

	@property
	def spin1(self):
		if self.spin1x is None and self.spin1y is None and self.spin1z is None:
			return None
		return numpy.array((self.spin1x, self.spin1y, self.spin1z), dtype = "double")

	@spin1.setter
	def spin1(self, spin):
		if spin is None:
			self.spin1x, self.spin1y, self.spin1z = None, None, None
		else:
			self.spin1x, self.spin1y, self.spin1z = spin

	@property
	def spin2(self):
		if self.spin2x is None and self.spin2y is None and self.spin2z is None:
			return None
		return numpy.array((self.spin2x, self.spin2y, self.spin2z), dtype = "double")

	@spin2.setter
	def spin2(self, spin):
		if spin is None:
			self.spin2x, self.spin2y, self.spin2z = None, None, None
		else:
			self.spin2x, self.spin2y, self.spin2z = spin

	def time_at_instrument(self, instrument, offsetvector):
		"""
		Return the "time" of the injection, delay corrected for the
		displacement from the geocentre to the given instrument.

		NOTE:  this method does not account for the rotation of the
		Earth that occurs during the transit of the plane wave from
		the detector to the geocentre.  That is, it is assumed the
		Earth is in the same orientation with respect to the
		celestial sphere when the wave passes through the detector
		as when it passes through the geocentre.  The Earth rotates
		by about 1.5 urad during the 21 ms it takes light to travel
		the radius of the Earth, which corresponds to 10 m of
		displacement at the equator, or 33 light-ns.  Therefore,
		the failure to do a proper retarded time calculation here
		results in errors as large as 33 ns.  This is insignificant
		in present applications, but be aware that this
		approximation is being made if the return value is used in
		other contexts.
		"""
		# the offset is subtracted from the time of the injection.
		# injections are done this way so that when the triggers
		# that result from an injection have the offset vector
		# added to their times the triggers will form a coinc
		t_geocent = self.time_geocent - offsetvector[instrument]
		ra, dec = self.ra_dec
		return t_geocent + lal.TimeDelayFromEarthCenter(lal.cached_detector_by_prefix[instrument].location, ra, dec, t_geocent)

	def snr_geometry_factors(self, instruments):
		"""
		Compute and return a dictionary of the ratios of the
		source's physical distance to its effective distances for
		each of the given instruments.  The expected SNR in a
		detector is

		rho_{0} = 8 * (D_horizon / D) * snr_geometry_factor,

		where D_horizon is the detector's horizon distance for this
		waveform (computed from the detector's noise spectral
		density), and D is the source's physical distance.  The
		geometry factor (what this method computes) depends on the
		direction to the source with respect to the antenna beam,
		the inclination of the source's orbital plane, and the wave
		frame's polarization.  The combination (D / geometry
		factor) is called the effective distance.  See Equation
		(4.3) of arXiv:0705.1514.

		See also .effective_distances(), .expected_snrs().
		"""
		cos2i = math.cos(self.inclination)**2.
		# don't rely on self.gmst to be set properly
		gmst = lal.GreenwichMeanSiderealTime(self.time_geocent)
		snr_geometry_factors = {}
		for instrument in instruments:
			fp, fc = lal.ComputeDetAMResponse(
				lal.cached_detector_by_prefix[instrument].response,
				self.longitude, self.latitude,
				self.polarization,
				gmst
			)
			snr_geometry_factors[instrument] = math.sqrt(fp**2. * (1. + cos2i)**2. / 4. + fc**2. * cos2i)
		return snr_geometry_factors

	def effective_distances(self, instruments):
		"""
		Compute and return a dictionary of the effective distances
		for this injection for the given instruments.  The expected
		SNR in a detector is

		rho_{0} = 8 * D_horizon / D_effective

		where D_effective, the effective distance, is related to
		the physical distance, D, by geometry factors

		D_effective = D / (geometry factors).

		See also .snr_geometry_factors(), .expected_snrs().
		"""
		return {instrument: self.distance / snr_geometry_factor for instrument, snr_geometry_factor in self.snr_geometry_factors(instruments).items()}

	def expected_snrs(self, horizon_distances):
		"""
		Compute and return a dictionary of the expected SNRs for
		this injection in the given instruments.  horizon_distances
		is a dictionary giving the horizon distance for each of the
		detectors for which an expected SNR is to be computed.  The
		expected SNR in a detector is

		rho_{0} = 8 * D_horizon / D_effective.

		See also .effective_distances().
		"""
		return {instrument: 8. * horizon_distances[instrument] / effective_distance for instrument, effective_distance in self.effective_distances(horizon_distances).items()}


SimInspiralTable.RowType = SimInspiral


#
# =============================================================================
#
#                               sim_burst:table
#
# =============================================================================
#


SimBurstID = table.next_id.type(u"simulation_id")


class SimBurstTable(table.Table):
	tableName = "sim_burst"
	validcolumns = {
		"process:process_id": "int_8s",
		"waveform": "lstring",
		"ra": "real_8",
		"dec": "real_8",
		"psi": "real_8",
		"time_geocent_gps": "int_4s",
		"time_geocent_gps_ns": "int_4s",
		"time_geocent_gmst": "real_8",
		"duration": "real_8",
		"frequency": "real_8",
		"bandwidth": "real_8",
		"q": "real_8",
		"pol_ellipse_angle": "real_8",
		"pol_ellipse_e": "real_8",
		"amplitude": "real_8",
		"hrss": "real_8",
		"egw_over_rsquared": "real_8",
		"waveform_number": "int_8u",
		"time_slide:time_slide_id": "int_8s",
		"simulation_id": "int_8s"
	}
	constraints = "PRIMARY KEY (simulation_id)"
	next_id = SimBurstID(0)


class SimBurst(table.Table.RowType):
	"""
	Example:

	>>> x = SimBurst()
	>>> x.ra_dec = 0., 0.
	>>> x.ra_dec
	(0.0, 0.0)
	>>> x.ra_dec = None
	>>> print(x.ra_dec)
	None
	>>> x.time_geocent = None
	>>> print(x.time_geocent)
	None
	>>> print(x.time_geocent_gmst)
	None
	>>> x.time_geocent = LIGOTimeGPS(6e8)
	>>> print(x.time_geocent)
	600000000
	>>> print(round(x.time_geocent_gmst, 8))
	-2238.39417156
	"""
	__slots__ = tuple(map(table.Column.ColumnName, SimBurstTable.validcolumns))

	time_geocent = gpsproperty_with_gmst("time_geocent_gps", "time_geocent_gps_ns", "time_geocent_gmst")

	@property
	def ra_dec(self):
		if self.ra is None and self.dec is None:
			return None
		return self.ra, self.dec

	@ra_dec.setter
	def ra_dec(self, radec):
		if radec is None:
			self.ra = self.dec = None
		else:
			self.ra, self.dec = radec

	def time_at_instrument(self, instrument, offsetvector):
		"""
		Return the "time" of the injection, delay corrected for the
		displacement from the geocentre to the given instrument.

		NOTE:  this method does not account for the rotation of the
		Earth that occurs during the transit of the plane wave from
		the detector to the geocentre.  That is, it is assumed the
		Earth is in the same orientation with respect to the
		celestial sphere when the wave passes through the detector
		as when it passes through the geocentre.  The Earth rotates
		by about 1.5 urad during the 21 ms it takes light to travel
		the radius of the Earth, which corresponds to 10 m of
		displacement at the equator, or 33 light-ns.  Therefore,
		the failure to do a proper retarded time calculation here
		results in errors as large as 33 ns.  This is insignificant
		for burst searches, but be aware that this approximation is
		being made if the return value is used in other contexts.
		"""
		# the offset is subtracted from the time of the injection.
		# injections are done this way so that when the triggers
		# that result from an injection have the offset vector
		# added to their times the triggers will form a coinc
		t_geocent = self.time_geocent - offsetvector[instrument]
		ra, dec = self.ra_dec
		return t_geocent + lal.TimeDelayFromEarthCenter(lal.cached_detector_by_prefix[instrument].location, ra, dec, t_geocent)


SimBurstTable.RowType = SimBurst


#
# =============================================================================
#
#                              sim_ringdown:table
#
# =============================================================================
#


SimRingdownID = table.next_id.type(u"simulation_id")


class SimRingdownTable(table.Table):
	tableName = "sim_ringdown"
	validcolumns = {
		"process:process_id": "int_8s",
		"waveform": "lstring",
		"coordinates": "lstring",
		"geocent_start_time": "int_4s",
		"geocent_start_time_ns": "int_4s",
		"h_start_time": "int_4s",
		"h_start_time_ns": "int_4s",
		"l_start_time": "int_4s",
		"l_start_time_ns": "int_4s",
		"v_start_time": "int_4s",
		"v_start_time_ns": "int_4s",
		"start_time_gmst": "real_8",
		"longitude": "real_4",
		"latitude": "real_4",
		"distance": "real_4",
		"inclination": "real_4",
		"polarization": "real_4",
		"frequency": "real_4",
		"quality": "real_4",
		"phase": "real_4",
		"mass": "real_4",
		"spin": "real_4",
		"epsilon": "real_4",
		"amplitude": "real_4",
		"eff_dist_h": "real_4",
		"eff_dist_l": "real_4",
		"eff_dist_v": "real_4",
		"hrss": "real_4",
		"hrss_h": "real_4",
		"hrss_l": "real_4",
		"hrss_v": "real_4",
		"simulation_id": "int_8s"
	}
	constraints = "PRIMARY KEY (simulation_id)"
	next_id = SimRingdownID(0)


class SimRingdown(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, SimRingdownTable.validcolumns))

	geocent_start = gpsproperty_with_gmst("geocent_start_time", "geocent_start_time_ns", "start_time_gmst")

	@property
	def ra_dec(self):
		if self.longitude is None and self.latitude is None:
			return None
		return self.longitude, self.latitude

	@ra_dec.setter
	def ra_dec(self, radec):
		if radec is None:
			self.longitude = self.latitude = None
		else:
			self.longitude, self.latitude = radec

	def time_at_instrument(self, instrument, offsetvector):
		"""
		Return the start time of the injection, delay corrected for
		the displacement from the geocentre to the given
		instrument.

		NOTE:  this method does not account for the rotation of the
		Earth that occurs during the transit of the plane wave from
		the detector to the geocentre.  That is, it is assumed the
		Earth is in the same orientation with respect to the
		celestial sphere when the wave passes through the detector
		as when it passes through the geocentre.  The Earth rotates
		by about 1.5 urad during the 21 ms it takes light to travel
		the radius of the Earth, which corresponds to 10 m of
		displacement at the equator, or 33 light-ns.  Therefore,
		the failure to do a proper retarded time calculation here
		results in errors as large as 33 ns.  This is insignificant
		for ring-down searches, but be aware that this
		approximation is being made if the return value is used in
		other contexts.
		"""
		# the offset is subtracted from the time of the injection.
		# injections are done this way so that when the triggers
		# that result from an injection have the offset vector
		# added to their times the triggers will form a coinc
		t_geocent = self.geocent_start - offsetvector[instrument]
		ra, dec = self.ra_dec
		return t_geocent + lal.TimeDelayFromEarthCenter(lal.cached_detector_by_prefix[instrument].location, ra, dec, t_geocent)


SimRingdownTable.RowType = SimRingdown


#
# =============================================================================
#
#                               summ_value:table
#
# =============================================================================
#


SummValueID = table.next_id.type(u"summ_value_id")


class SummValueTable(table.Table):
	tableName = "summ_value"
	validcolumns = {
		"summ_value_id": "int_8s",
		"program": "lstring",
		"process:process_id": "int_8s",
		"frameset_group": "lstring",
		"segment_definer:segment_def_id": "int_8s",
		"start_time": "int_4s",
		"start_time_ns": "int_4s",
		"end_time": "int_4s",
		"end_time_ns": "int_4s",
		"ifo": "lstring",
		"name": "lstring",
		"value": "real_4",
		"error": "real_4",
		"intvalue": "int_4s",
		"comment": "lstring"
	}
	constraints = "PRIMARY KEY (summ_value_id)"
	next_id = SummValueID(0)


class SummValue(table.Table.RowType):
	"""
	Example:

	>>> x = SummValue()
	>>> x.instruments = (u"H1", u"L1")
	>>> print(x.ifo)
	H1,L1
	>>> assert x.instruments == set([u'H1', u'L1'])
	>>> x.start = LIGOTimeGPS(0)
	>>> x.end = LIGOTimeGPS(10)
	>>> x.segment
	segment(LIGOTimeGPS(0, 0), LIGOTimeGPS(10, 0))
	>>> x.segment = None
	>>> print(x.segment)
	None
	"""
	__slots__ = tuple(map(table.Column.ColumnName, SummValueTable.validcolumns))

	instruments = instrumentsproperty("ifo")

	start = gpsproperty("start_time", "start_time_ns")
	end = gpsproperty("end_time", "end_time_ns")
	segment = segmentproperty("start", "end")


SummValueTable.RowType = SummValue


#
# =============================================================================
#
#                                segment:table
#
# =============================================================================
#


SegmentID = table.next_id.type(u"segment_id")


class SegmentTable(table.Table):
	tableName = "segment"
	validcolumns = {
		"creator_db": "int_4s",
		"process:process_id": "int_8s",
		"segment_id": "int_8s",
		"start_time": "int_4s",
		"start_time_ns": "int_4s",
		"end_time": "int_4s",
		"end_time_ns": "int_4s",
		"segment_definer:segment_def_id": "int_8s",
		"segment_def_cdb": "int_4s"
	}
	constraints = "PRIMARY KEY (segment_id)"
	next_id = SegmentID(0)


@functools.total_ordering
class Segment(table.Table.RowType):
	"""
	Example:

	>>> x = Segment()
	>>> x.start = LIGOTimeGPS(0)
	>>> x.end = LIGOTimeGPS(10)
	>>> x.segment
	segment(LIGOTimeGPS(0, 0), LIGOTimeGPS(10, 0))
	>>> x.segment = None
	>>> print(x.segment)
	None
	>>> print(x.start)
	None
	>>> # non-LIGOTimeGPS times are converted to LIGOTimeGPS
	>>> x.segment = (20, 30.125)
	>>> x.end
	LIGOTimeGPS(30, 125000000)
	>>> # initialization from a tuple or with arguments
	>>> Segment((20, 30)).segment
	segment(LIGOTimeGPS(20, 0), LIGOTimeGPS(30, 0))
	>>> Segment(20, 30).segment
	segment(LIGOTimeGPS(20, 0), LIGOTimeGPS(30, 0))
	>>> # use as a segment object in segmentlist operations
	>>> from ligo import segments
	>>> x = segments.segmentlist([Segment(0, 10), Segment(20, 30)])
	>>> abs(x)
	LIGOTimeGPS(20, 0)
	>>> y = segments.segmentlist([Segment(5, 15), Segment(25, 35)])
	>>> abs(x & y)
	LIGOTimeGPS(10, 0)
	>>> abs(x | y)
	LIGOTimeGPS(30, 0)
	>>> 8.0 in x
	True
	>>> 12 in x
	False
	>>> Segment(2, 3) in x
	True
	>>> Segment(2, 12) in x
	False
	>>> segments.segment(2, 3) in x
	True
	>>> segments.segment(2, 12) in x
	False
	>>> # make sure results are segment table row objects
	>>> segments.segmentlist(map(Segment, x & y))	# doctest: +ELLIPSIS
	[<ligo.lw.lsctables.Segment object at 0x...>, <ligo.lw.lsctables.Segment object at 0x...>]

	Unbounded intervals are permitted.  See gpsproperty for information
	on the encoding scheme used internally, and its limitations.

	Example:

	>>> x = Segment()
	>>> # OK
	>>> x.start = -segments.infinity()
	>>> # also OK
	>>> x.start = float("-inf")
	>>> # infinite boundaries always returned as segments.infinity
	>>> # instances
	>>> x.start
	-infinity
	>>> x.end = float("+inf")
	>>> x.segment
	segment(-infinity, infinity)
	"""
	__slots__ = tuple(map(table.Column.ColumnName, SegmentTable.validcolumns))

	start = gpsproperty("start_time", "start_time_ns")
	end = gpsproperty("end_time", "end_time_ns")
	segment = segmentproperty("start", "end")

	# emulate a ligo.segments.segment object

	def __abs__(self):
		return abs(self.segment)

	def __lt__(self, other):
		return self.segment < other

	def __eq__(self, other):
		return self.segment == other

	def __contains__(self, other):
		return other in self.segment

	def __getitem__(self, i):
		return self.segment[i]

	def __init__(self, *args, **kwargs):
		if args:
			try:
				# first try unpacking arguments
				self.segment = args
			except ValueError:
				# didn't work, try unpacking 0th argument
				self.segment, = args
		for key, value in kwargs.items():
			setattr(self, key, value)

	def __len__(self):
		return len(self.segment)

	def __nonzero__(self):
		return bool(self.segment)


SegmentTable.RowType = Segment


#
# =============================================================================
#
#                            segment_definer:table
#
# =============================================================================
#


SegmentDefID = table.next_id.type(u"segment_def_id")


class SegmentDefTable(table.Table):
	tableName = "segment_definer"
	validcolumns = {
		"creator_db": "int_4s",
		"process:process_id": "int_8s",
		"segment_def_id": "int_8s",
		"ifos": "lstring",
		"name": "lstring",
		"version": "int_4s",
		"comment": "lstring",
		"insertion_time": "int_4s"
	}
	constraints = "PRIMARY KEY (segment_def_id)"
	next_id = SegmentDefID(0)


class SegmentDef(table.Table.RowType):
	"""
	Example:

	>>> x = SegmentDef()
	>>> x.instruments = (u"H1", u"L1")
	>>> print(x.ifos)
	H1,L1
	>>> assert x.instruments == set([u'H1', u'L1'])
	"""
	__slots__ = tuple(map(table.Column.ColumnName, SegmentDefTable.validcolumns))

	instruments = instrumentsproperty("ifos")


SegmentDefTable.RowType = SegmentDef


#
# =============================================================================
#
#                            segment_summary:table
#
# =============================================================================
#


SegmentSumID = table.next_id.type(u"segment_sum_id")


class SegmentSumTable(table.Table):
	tableName = "segment_summary"
	validcolumns = {
		"creator_db": "int_4s",
		"process:process_id": "int_8s",
		"segment_sum_id": "int_8s",
		"start_time": "int_4s",
		"start_time_ns": "int_4s",
		"end_time": "int_4s",
		"end_time_ns": "int_4s",
		"comment": "lstring",
		"segment_definer:segment_def_id": "int_8s",
		"segment_def_cdb": "int_4s"
	}
	constraints = "PRIMARY KEY (segment_sum_id)"
	next_id = SegmentSumID(0)

	def get(self, segment_def_id = None):
		"""
		Return a segmentlist object describing the times spanned by
		the segments carrying the given segment_def_id.  If
		segment_def_id is None then all segments are returned.

		Note:  the result is not coalesced, the segmentlist
		contains the segments as they appear in the table.
		"""
		if segment_def_id is None:
			return segments.segmentlist(row.segment for row in self)
		return segments.segmentlist(row.segment for row in self if row.segment_def_id == segment_def_id)


class SegmentSum(Segment):
	__slots__ = tuple(map(table.Column.ColumnName, SegmentSumTable.validcolumns))

	start = gpsproperty("start_time", "start_time_ns")
	end = gpsproperty("end_time", "end_time_ns")
	segment = segmentproperty("start", "end")


SegmentSumTable.RowType = SegmentSum


#
# =============================================================================
#
#                               time_slide:table
#
# =============================================================================
#


TimeSlideID = table.next_id.type(u"time_slide_id")


class TimeSlideTable(table.Table):
	tableName = "time_slide"
	validcolumns = {
		"process:process_id": "int_8s",
		"time_slide_id": "int_8s",
		"instrument": "lstring",
		"offset": "real_8"
	}
	constraints = "PRIMARY KEY (time_slide_id, instrument)"
	next_id = TimeSlideID(0)

	def as_dict(self):
		"""
		Return a dictionary mapping time slide IDs to offset
		dictionaries.

		NOTE:  very little checking is done, e.g., for repeated
		instruments for a given ID (which could suggest an ID
		collision).
		"""
		# import is done here to reduce risk of a cyclic
		# dependency.  at the time of writing there is not one, but
		# we can help prevent it in the future by putting this
		# here.
		from lalburst.offsetvector import offsetvector
		return dict((time_slide_id, offsetvector((row.instrument, row.offset) for row in rows)) for time_slide_id, rows in itertools.groupby(sorted(self, key = lambda row: row.time_slide_id), lambda row: row.time_slide_id))

	def append_offsetvector(self, offsetvect, process):
		"""
		Append rows describing an instrument --> offset mapping to
		this table.  offsetvect is a dictionary mapping instrument
		to offset.  process should be the row in the process table
		on which the new time_slide table rows will be blamed (or
		any object with a process_id attribute).  The return value
		is the time_slide_id assigned to the new rows.
		"""
		time_slide_id = self.get_next_id()
		for instrument, offset in offsetvect.items():
			self.append(self.RowType(
				process_id = process.process_id,
				time_slide_id = time_slide_id,
				instrument = instrument,
				offset = offset
			))
		return time_slide_id

	def get_time_slide_id(self, offsetdict, create_new = None, superset_ok = False, nonunique_ok = False):
		"""
		Return the time_slide_id corresponding to the offset vector
		described by offsetdict, a dictionary of instrument/offset
		pairs.

		If the optional create_new argument is None (the default),
		then the table must contain a matching offset vector.  The
		return value is the ID of that vector.  If the table does
		not contain a matching offset vector then KeyError is
		raised.

		If the optional create_new argument is set to a Process
		object (or any other object with a process_id attribute),
		then if the table does not contain a matching offset vector
		a new one will be added to the table and marked as having
		been created by the given process.  The return value is the
		ID of the (possibly newly created) matching offset vector.

		If the optional superset_ok argument is False (the default)
		then an offset vector in the table is considered to "match"
		the requested offset vector only if they contain the exact
		same set of instruments.  If the superset_ok argument is
		True, then an offset vector in the table is considered to
		match the requested offset vector as long as it provides
		the same offsets for the same instruments as the requested
		vector, even if it provides offsets for other instruments
		as well.

		More than one offset vector in the table might match the
		requested vector.  If the optional nonunique_ok argument is
		False (the default), then KeyError will be raised if more
		than one offset vector in the table is found to match the
		requested vector.  If the optional nonunique_ok is True
		then the return value is the ID of one of the matching
		offset vectors selected at random.
		"""
		# look for matching offset vectors
		if superset_ok:
			ids = [time_slide_id for time_slide_id, slide in self.as_dict().items() if offsetdict == dict((instrument, offset) for instrument, offset in slide.items() if instrument in offsetdict)]
		else:
			ids = [time_slide_id for time_slide_id, slide in self.as_dict().items() if offsetdict == slide]
		if len(ids) > 1:
			# found more than one
			if nonunique_ok:
				# and that's OK
				return ids[0]
			# and that's not OK
			raise KeyError("%s not unique" % repr(offsetdict))
		if len(ids) == 1:
			# found one
			return ids[0]
		# offset vector not found in table
		if create_new is None:
			# and that's not OK
			raise KeyError("%s not found" % repr(offsetdict))
		# that's OK, create new vector, return its ID
		return self.append_offsetvector(offsetdict, create_new)


class TimeSlide(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, TimeSlideTable.validcolumns))


TimeSlideTable.RowType = TimeSlide


#
# =============================================================================
#
#                             coinc_definer:table
#
# =============================================================================
#


CoincDefID = table.next_id.type(u"coinc_def_id")


class CoincDefTable(table.Table):
	tableName = "coinc_definer"
	validcolumns = {
		"coinc_def_id": "int_8s",
		"search": "lstring",
		"search_coinc_type": "int_4u",
		"description": "lstring"
	}
	constraints = "PRIMARY KEY (coinc_def_id)"
	next_id = CoincDefID(0)
	how_to_index = {
		"cd_ssct_index": ("search", "search_coinc_type")
	}

	def get_coinc_def_id(self, search, search_coinc_type, create_new = True, description = None):
		"""
		Return the coinc_def_id for the row in the table whose
		search string and search_coinc_type integer have the values
		given.  If a matching row is not found, the default
		behaviour is to create a new row and return the ID assigned
		to the new row.  If, instead, create_new is False then
		KeyError is raised when a matching row is not found.  The
		optional description parameter can be used to set the
		description string assigned to the new row if one is
		created, otherwise the new row is left with no description.
		"""
		# look for the ID
		rows = [row for row in self if (row.search, row.search_coinc_type) == (search, search_coinc_type)]
		if len(rows) > 1:
			raise ValueError("(search, search coincidence type) = ('%s', %d) is not unique" % (search, search_coinc_type))
		if len(rows) > 0:
			return rows[0].coinc_def_id

		# coinc type not found in table
		if not create_new:
			raise KeyError((search, search_coinc_type))
		coinc_def_id = self.get_next_id()
		self.append(self.RowType(
			coinc_def_id = coinc_def_id,
			search = search,
			search_coinc_type = search_coinc_type,
			description = description
		))

		# return new ID
		return coinc_def_id


class CoincDef(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, CoincDefTable.validcolumns))


CoincDefTable.RowType = CoincDef


#
# =============================================================================
#
#                              coinc_event:table
#
# =============================================================================
#


CoincID = table.next_id.type(u"coinc_event_id")


class CoincTable(table.Table):
	tableName = "coinc_event"
	validcolumns = {
		"process:process_id": "int_8s",
		"coinc_definer:coinc_def_id": "int_8s",
		"coinc_event_id": "int_8s",
		"time_slide:time_slide_id": "int_8s",
		"instruments": "lstring",
		"nevents": "int_4u",
		"likelihood": "real_8"
	}
	constraints = "PRIMARY KEY (coinc_event_id)"
	next_id = CoincID(0)
	how_to_index = {
		"ce_cdi_index": ("coinc_def_id",),
		"ce_tsi_index": ("time_slide_id",)
	}


class Coinc(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, CoincTable.validcolumns))

	insts = instrumentsproperty("instruments")


CoincTable.RowType = Coinc


#
# =============================================================================
#
#                            coinc_event_map:table
#
# =============================================================================
#


class CoincMapTable(table.Table):
	tableName = "coinc_event_map"
	validcolumns = {
		"coinc_event:coinc_event_id": "int_8s",
		"table_name": "char_v",
		"event_id": "int_8s"
	}
	how_to_index = {
		"cem_tn_ei_index": ("table_name", "event_id"),
		"cem_cei_index": ("coinc_event_id",)
	}

	def applyKeyMapping(self, mapping):
		table_column = self.getColumnByName("table_name")
		event_id_column = self.getColumnByName("event_id")
		coinc_event_id_column = self.getColumnByName("coinc_event_id")
		for i, (table_name, old_event_id, old_coinc_event_id) in enumerate(zip(table_column, event_id_column, coinc_event_id_column)):
			try:
				event_id_column[i] = mapping[table_name, old_event_id]
			except KeyError:
				pass
			try:
				coinc_event_id_column[i] = mapping["coinc_event", old_coinc_event_id]
			except KeyError:
				pass


class CoincMap(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, CoincMapTable.validcolumns))


CoincMapTable.RowType = CoincMap


#
# =============================================================================
#
#                                dq_list Table
#
# =============================================================================
#


DQSpecListID = table.next_id.type(u"dq_list_id")
DQSpecListRowID = table.next_id.type(u"dq_list_row_id")


class DQSpecListTable(table.Table):
	tableName = "dq_list"
	validcolumns = {
		"dq_list:dq_list_id": "int_8s",
		"dq_list_row_id": "int_8s",
		"instrument": "lstring",
		"flag": "lstring",
		"low_window": "real_8",
		"high_window": "real_8"
	}
	constraints = "PRIMARY KEY (dq_list_id, dq_list_row_id)"
	next_id = DQSpecListID(0)


class DQSpec(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, DQSpecListTable.validcolumns))

	def apply_to_segmentlist(self, seglist):
		"""
		Apply our low and high windows to the segments in a
		segmentlist.
		"""
		for i, seg in enumerate(seglist):
			seglist[i] = seg.__class__(seg[0] - self.low_window, seg[1] + self.high_window)


DQSpecListTable.RowType = DQSpec


#
# =============================================================================
#
#                            veto_definer:table
#
# =============================================================================
#


class VetoDefTable(table.Table):
	tableName = "veto_definer"
	validcolumns = {
		"process:process_id": "int_8s",
		"ifo": "lstring",
		"name": "lstring",
		"version": "int_4s",
		"category": "int_4s",
		"start_time": "int_4s",
		"end_time": "int_4s",
		"start_pad": "int_4s",
		"end_pad": "int_4s",
		"comment": "lstring"
	}

	def versions(self, name, category):
		"""
		Report the versions available for the (name, category)
		pair.
		"""
		return set(row.version for row in self if row.name == name and row.category == category)

	def segmentlistdict(self, name, category, version = None, padded = False):
		"""
		Return a segments.segmentlistdict mapping instrument to the
		segments for the (name, category) pair.  If version is None
		(the default) then the newest version of the segments are
		reported, otherwise the segments for the requested version
		are reported.  If padded is boolean False (the default) the
		non-padded segments are reported, otherwise the padded
		segments are reported.
		"""
		seglists = segments.segmentlistdict()
		if version is None:
			# not an error if there are no versions, just means
			# the segmentlists are empty
			version = max(self.versions(name, category) or (None,))
		for row in self:
			if row.name != name or row.category != category or row.version != version:
				continue
			try:
				seglist = seglists[row.ifo]
			except KeyError:
				seglist = seglists[row.ifo] = segments.segmentlist()
			seglist.append(row.segment_padded if padded else row.segment)
		return seglists


class VetoDef(table.Table.RowType):
	__slots__ = tuple(map(table.Column.ColumnName, VetoDefTable.validcolumns))

	# because detchar refuses to allow vetoes to have non-integer
	# boundaries, even in principle (i.e., by designing out the choice
	# altogether, regardless current use), we have a problem
	# interfacing to this table using standard tools.  to work-around
	# the problem virtual nanoseconds columns are emulated, which
	# always truncate towards 0.

	@property
	def start_time_ns(eslf):
		return 0
	@start_time_ns.setter
	def start_time_ns(self, val):
		pass

	@property
	def end_time_ns(eslf):
		return 0
	@end_time_ns.setter
	def end_time_ns(self, val):
		pass

	# now we can provide easier interfaces to the start and stop pair

	start = gpsproperty("start_time", "start_time_ns")
	end = gpsproperty("end_time", "end_time_ns")
	segment = gpsproperty("start", "end")

	@property
	def start_padded(self):
		return self.start - self.start_pad
	@property
	def end_padded(self):
		return self.end + self.end_pad

	segment_padded = gpsproperty("start_padded", "end_padded")


VetoDefTable.RowType = VetoDef


#
# =============================================================================
#
#                                Table Metadata
#
# =============================================================================
#


#
# Table name ---> table type mapping.
#


TableByName = {
	CoincDefTable.tableName: CoincDefTable,
	CoincInspiralTable.tableName: CoincInspiralTable,
	CoincMapTable.tableName: CoincMapTable,
	CoincRingdownTable.tableName: CoincRingdownTable,
	CoincTable.tableName: CoincTable,
	DQSpecListTable.tableName: DQSpecListTable,
	ProcessParamsTable.tableName: ProcessParamsTable,
	ProcessTable.tableName: ProcessTable,
	SearchSummaryTable.tableName: SearchSummaryTable,
	SearchSummVarsTable.tableName: SearchSummVarsTable,
	SegmentDefTable.tableName: SegmentDefTable,
	SegmentSumTable.tableName: SegmentSumTable,
	SegmentTable.tableName: SegmentTable,
	SimBurstTable.tableName: SimBurstTable,
	SimInspiralTable.tableName: SimInspiralTable,
	SimRingdownTable.tableName: SimRingdownTable,
	SnglBurstTable.tableName: SnglBurstTable,
	SnglInspiralTable.tableName: SnglInspiralTable,
	SnglRingdownTable.tableName: SnglRingdownTable,
	SummValueTable.tableName: SummValueTable,
	TimeSlideTable.tableName: TimeSlideTable,
	VetoDefTable.tableName: VetoDefTable
}


def reset_next_ids(classes):
	"""
	For each class in the list, if the .next_id attribute is not None
	(meaning the table has an ID generator associated with it), set
	.next_id to 0.  This has the effect of reseting the ID generators,
	and is useful in applications that process multiple documents and
	add new rows to tables in those documents.  Calling this function
	between documents prevents new row IDs from growing continuously
	from document to document.  There is no need to do this, it's
	purpose is merely aesthetic, but it can be confusing to open a
	document and find process ID 300 in the process table and wonder
	what happened to the other 299 processes.

	Example:

	>>> reset_next_ids(TableByName.values())
	"""
	for cls in classes:
		cls.reset_next_id()


#
# =============================================================================
#
#                               Content Handler
#
# =============================================================================
#


#
# Override portions of a ligolw.LIGOLWContentHandler class
#


def use_in(ContentHandler):
	"""
	Modify ContentHandler, a sub-class of
	ligo.lw.ligolw.LIGOLWContentHandler, to cause it to use the Table
	classes defined in this module when parsing XML documents.

	Example:

	>>> from ligo.lw import ligolw
	>>> class MyContentHandler(ligolw.LIGOLWContentHandler):
	...	pass
	...
	>>> use_in(MyContentHandler)
	<class 'ligo.lw.lsctables.MyContentHandler'>
	"""
	ContentHandler = table.use_in(ContentHandler)

	def startTable(self, parent, attrs, __orig_startTable = ContentHandler.startTable):
		name = table.Table.TableName(attrs[u"Name"])
		if name in TableByName:
			return TableByName[name](attrs)
		return __orig_startTable(self, parent, attrs)

	ContentHandler.startTable = startTable

	return ContentHandler
