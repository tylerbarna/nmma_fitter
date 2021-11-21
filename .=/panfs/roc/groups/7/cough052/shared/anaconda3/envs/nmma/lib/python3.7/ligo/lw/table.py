# Copyright (C) 2006--2017  Kipp Cannon
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
While the ligolw module provides classes and parser support for reading and
writing LIGO Light Weight XML documents, this module supplements that code
with classes and parsers that add intelligence to the in-RAM document
representation.

In particular, the document tree associated with a Table element is
enhanced.  During parsing, the Stream element in this module converts the
character data contained within it into a list of objects.  The list
contains one object for each row of the table, and the objects' attributes
are the names of the table's columns.  When the document is written out
again, the Stream element serializes the row objects back into character
data.

The Table element exports a list-like interface to the rows.  The Column
elements also provide list-like access to the values in the corresponding
columns of the table.
"""


import copy
import itertools
import re
import sys
from xml.sax.saxutils import escape as xmlescape
from xml.sax.xmlreader import AttributesImpl


from . import __author__, __date__, __version__
from . import ligolw
from . import tokenizer
from . import types as ligolwtypes


#
# =============================================================================
#
#                                  Utilities
#
# =============================================================================
#


def get_table(xmldoc, name):
	"""
	Scan xmldoc for a Table element named name.  Raises ValueError if
	not exactly 1 such table is found.

	See also the .get_table() class method of the Table class.
	"""
	return Table.get_table(xmldoc, name)


class next_id(int):
	"""
	Type for .next_id attributes of tables with int_8s ID columns.
	"""
	column_name = None

	def __add__(self, other):
		return type(self)(super(next_id, self).__add__(other))

	@classmethod
	def type(cls, column_name):
		return type(str("next_%s" % column_name), (cls,), {"column_name": column_name})


def reassign_ids(elem):
	"""
	Recurses over all Table elements below elem whose next_id
	attributes are not None, and uses the .get_next_id() method of each
	of those Tables to generate and assign new IDs to their rows.  The
	modifications are recorded, and finally all ID attributes in all
	rows of all tables are updated to fix cross references to the
	modified IDs.

	This function is used by ligolw_add to assign new IDs to rows when
	merging documents in order to make sure there are no ID collisions.
	Using this function in this way requires the .get_next_id() methods
	of all Table elements to yield unused IDs, otherwise collisions
	will result anyway.  See the .sync_next_id() method of the Table
	class for a way to initialize the .next_id attributes so that
	collisions will not occur.

	Example:

	>>> from ligo.lw import ligolw
	>>> from ligo.lw import lsctables
	>>> xmldoc = ligolw.Document()
	>>> xmldoc.appendChild(ligolw.LIGO_LW()).appendChild(lsctables.New(lsctables.SnglInspiralTable))
	[]
	>>> reassign_ids(xmldoc)
	"""
	mapping = {}
	for tbl in elem.getElementsByTagName(ligolw.Table.tagName):
		if tbl.next_id is not None:
			tbl.updateKeyMapping(mapping)
	for tbl in elem.getElementsByTagName(ligolw.Table.tagName):
		tbl.applyKeyMapping(mapping)


#
# =============================================================================
#
#                                Column Element
#
# =============================================================================
#


class Column(ligolw.Column):
	"""
	High-level column element that provides list-like access to the
	values in a column.

	Example:

	>>> from xml.sax.xmlreader import AttributesImpl
	>>> import sys
	>>> tbl = Table(AttributesImpl({u"Name": u"test"}))
	>>> col = tbl.appendChild(Column(AttributesImpl({u"Name": u"test:snr", u"Type": u"real_8"})))
	>>> tbl.appendChild(TableStream(AttributesImpl({u"Name": u"test"})))	# doctest: +ELLIPSIS
	<ligo.lw.table.TableStream object at ...>
	>>> print(col.Name)
	snr
	>>> print(col.Type)
	real_8
	>>> print(col.table_name)
	test
	>>> # append 3 rows (with nothing in them)
	>>> tbl.append(tbl.RowType())
	>>> tbl.append(tbl.RowType())
	>>> tbl.append(tbl.RowType())
	>>> # assign values to the rows, in order, in this column
	>>> col[:] = [8.0, 10.0, 12.0]
	>>> col[:]
	[8.0, 10.0, 12.0]
	>>> col.asarray()	# doctest: +NORMALIZE_WHITESPACE
	array([ 8., 10., 12.])
	>>> tbl.write(sys.stdout)	# doctest: +NORMALIZE_WHITESPACE
	<Table Name="test">
		<Column Name="test:snr" Type="real_8"/>
		<Stream Name="test">
			8,
			10,
			12
		</Stream>
	</Table>
	>>> col.index(10)
	1
	>>> 12 in col
	True
	>>> col[0] = 9.
	>>> col[1] = 9.
	>>> col[2] = 9.
	>>> tbl.write(sys.stdout)		# doctest: +NORMALIZE_WHITESPACE
	<Table Name="test">
		<Column Name="test:snr" Type="real_8"/>
		<Stream Name="test">
			9,
			9,
			9
		</Stream>
	</Table>
	>>> col.count(9)
	3

	NOTE:  the .Name attribute returns the stripped "Name" attribute of
	the element, e.g. with the table name prefix removed, but when
	assigning to the .Name attribute the value provided is stored
	without modification, i.e. there is no attempt to reattach the
	table's name to the string.  The calling code is responsible for
	doing the correct manipulations.  Therefore, the assignment
	operation below

	>>> print(col.Name)
	snr
	>>> print(col.getAttribute("Name"))
	test:snr
	>>> col.Name = col.Name
	>>> print(col.Name)
	snr
	>>> print(col.getAttribute("Name"))
	snr

	does not preserve the value of the "Name" attribute (though it does
	preserve the stripped form reported by the .Name property).  This
	asymmetry is necessary because the correct table name string to
	reattach to the attribute's value cannot always be known, e.g., if
	the Column object is not part of an XML tree and does not have a
	parent node.
	"""
	# FIXME: the pattern should be
	#
	# r"(?:\A[a-z0-9_]+:|\A)(?P<FullName>(?:[a-z0-9_]+:|\A)(?P<Name>[a-z0-9_]+))\Z"
	#
	# but people are putting upper case letters in names!!!!!  Someone
	# is going to get the beats.  There is a reason for requiring names
	# to be all lower case:  SQL table and column names are case
	# insensitive, therefore (i) when converting a document to SQL the
	# columns "Rho" and "rho" would become indistinguishable and so it
	# would be impossible to convert a document with columns having
	# names like this into an SQL database;  and (ii) even if that
	# degeneracy is not encountered the case cannot be preserved and so
	# when converting back to XML the correct capitalization is lost.
	# Requiring names to be all lower-case creates the same
	# degeneracies in XML representations that exist in SQL
	# representations ensuring compatibility and defines the correct
	# case to restore the names to when converting to XML.  Other rules
	# can be imagined that would work as well, this is the one that got
	# chosen.
	class ColumnName(ligolw.LLWNameAttr):
		dec_pattern = re.compile(r"(?:\A\w+:|\A)(?P<FullName>(?:(?P<Table>\w+):|\A)(?P<Name>\w+))\Z")
		enc_pattern = u"%s"

		@classmethod
		def table_name(cls, name):
			"""
			Example:

			>>> Column.ColumnName.table_name("process:process_id")
			'process'
			>>> Column.ColumnName.table_name("process_id")
			Traceback (most recent call last):
			  File "<stdin>", line 1, in <module>
			ValueError: table name not found in 'process_id'
			"""
			table_name = cls.dec_pattern.match(name).group("Table")
			if table_name is None:
				raise ValueError("table name not found in '%s'" % name)
			return table_name

	Name = ligolw.attributeproxy(u"Name", enc = ColumnName.enc, dec = ColumnName)

	@property
	def table_name(self):
		return self.ColumnName.table_name(self.getAttribute("Name"))

	def __len__(self):
		"""
		The number of values in this column.
		"""
		return len(self.parentNode)

	def __getitem__(self, i):
		"""
		Retrieve the value in this column in row i.
		"""
		if isinstance(i, slice):
			return [getattr(r, self.Name) for r in self.parentNode[i]]
		else:
			return getattr(self.parentNode[i], self.Name)

	def __setitem__(self, i, value):
		"""
		Set the value in this column in row i.  i may be a slice.

		NOTE:  Unlike normal Python lists, the length of the Column
		cannot be changed as it is tied to the number of rows in
		the Table.  Therefore, if i is a slice, value should be an
		iterable with exactly the correct number of items.  No
		check is performed to ensure that this is true:  if value
		contains too many items the extras will be ignored, and if
		value contains too few items only as many rows will be
		updated as there are items.
		"""
		if isinstance(i, slice):
			for r, val in zip(self.parentNode[i], value):
				setattr(r, self.Name, val)
		else:
			setattr(self.parentNode[i], self.Name, value)

	def __delitem__(self, *args):
		raise NotImplementedError

	def __iter__(self):
		"""
		Return an iterator object for iterating over values in this
		column.
		"""
		for row in self.parentNode:
			yield getattr(row, self.Name)

	def count(self, value):
		"""
		Return the number of rows with this column equal to value.
		"""
		return sum(x == value for x in self)

	def index(self, value):
		"""
		Return the smallest index of the row(s) with this column
		equal to value.
		"""
		for i, x in enumerate(self):
			if x == value:
				return i
		raise ValueError(value)

	def __contains__(self, value):
		"""
		Returns True or False if there is or is not, respectively,
		a row containing val in this column.
		"""
		return value in iter(self)

	def asarray(self):
		"""
		Construct a numpy array from this column.  Note that this
		creates a copy of the data, so modifications made to the
		array will *not* be recorded in the original document.
		"""
		# most codes don't use this feature, this is the only place
		# numpy is used here, and importing numpy can be
		# time-consuming, so we defer the import until needed.
		import numpy
		try:
			dtype = ligolwtypes.ToNumPyType[self.Type]
		except KeyError as e:
			raise TypeError("cannot determine numpy dtype for Column '%s': %s" % (self.getAttribute("Name"), e))
		return numpy.fromiter(self, dtype = dtype)

	@classmethod
	def getColumnsByName(cls, elem, name):
		"""
		Return a list of Column elements named name under elem.
		"""
		name = cls.ColumnName(name)
		return elem.getElements(lambda e: (e.tagName == cls.tagName) and (e.Name == name))


#
# =============================================================================
#
#                                Stream Element
#
# =============================================================================
#


#
# Stream class
#


class TableStream(ligolw.Stream):
	"""
	High-level Stream element for use inside Tables.  This element
	knows how to parse the delimited character stream into row objects
	that it appends into the list-like parent element, and knows how to
	turn the parent's rows back into a character stream.
	"""
	#
	# Select the RowBuilder class to use when parsing tables.
	#

	RowBuilder = tokenizer.RowBuilder

	def config(self, parentNode):
		# some initialization that requires access to the
		# parentNode, and so cannot be done inside the __init__()
		# function.
		loadcolumns = set(parentNode.columnnames)
		if parentNode.loadcolumns is not None:
			# FIXME:  convert loadcolumns attributes to sets to
			# avoid the conversion.
			loadcolumns &= set(parentNode.loadcolumns)
		self._tokenizer = tokenizer.Tokenizer(self.Delimiter)
		self._tokenizer.set_types([(pytype if colname in loadcolumns else None) for pytype, colname in zip(parentNode.columnpytypes, parentNode.columnnames)])
		self._rowbuilder = self.RowBuilder(parentNode.RowType, [name for name in parentNode.columnnames if name in loadcolumns])
		return self

	def appendData(self, content):
		# tokenize buffer, pack into row objects, and append to
		# table
		appendfunc = self.parentNode.append
		for row in self._rowbuilder.append(self._tokenizer.append(content)):
			appendfunc(row)

	def endElement(self):
		# stream tokenizer uses delimiter to identify end of each
		# token, so add a final delimiter to induce the last token
		# to get parsed but only if there's something other than
		# whitespace left in the tokenizer's buffer.  the writing
		# code will have put a final delimiter into the stream if
		# the final token was pure whitespace in order to
		# unambiguously indicate that token's presence
		if not self._tokenizer.data.isspace():
			self.appendData(self.Delimiter)
		# now we're done with these
		del self._tokenizer
		del self._rowbuilder

	def write(self, fileobj = sys.stdout, indent = u""):
		# retrieve the .write() method of the file object to avoid
		# doing the attribute lookup in loops
		w = fileobj.write
		# loop over parent's rows.  This is complicated because we
		# need to not put a delimiter at the end of the last row
		# unless it ends with a null token
		w(self.start_tag(indent))
		rowdumper = tokenizer.RowDumper(self.parentNode.columnnames, [ligolwtypes.FormatFunc[coltype] for coltype in self.parentNode.columntypes], self.Delimiter)
		rowdumper.dump(self.parentNode)
		try:
			line = next(rowdumper)
		except StopIteration:
			# table is empty
			pass
		else:
			# write first row
			newline = u"\n" + indent + ligolw.Indent
			w(newline)
			# the xmlescape() call replaces things like "<"
			# with "&lt;" so that the string will not confuse
			# an XML parser when the file is read.  turning
			# "&lt;" back into "<" during file reading is
			# handled by the XML parser, so there is no code
			# in this library related to that.
			w(xmlescape(line))
			# now add delimiter and write the remaining rows
			newline = rowdumper.delimiter + newline
			for line in rowdumper:
				w(newline)
				w(xmlescape(line))
			if rowdumper.tokens and rowdumper.tokens[-1] == u"":
				# the last token of the last row was null:
				# add a final delimiter to indicate that a
				# token is present
				w(rowdumper.delimiter)
		w(u"\n" + self.end_tag(indent) + u"\n")


#
# =============================================================================
#
#                                Table Element
#
# =============================================================================
#


class Table(ligolw.Table, list):
	"""
	High-level Table element that knows about its columns and rows.

	Special Attributes
	------------------

	These are used by table-specific subclasses to provide information
	about the table they define.  Set to None when not used.

	.validcolumns:  Dictionary of column name/type pairs defining the
	set of columns instances of this table may have.

	.loadcolumns:  Sequence of names of columns to be loaded.  If not
	None, only names appearing in the list will be loaded, the rest
	will be skipped.  Can be used to reduce memory use.

	.constraints:  Text to be included as constraints in the SQL
	statement used to construct the table.

	.how_to_index:  Dictionary mapping SQL index name to an interable
	of column names over which to construct that index.

	.next_id:  object giving the next ID to assign to a row in this
	table, and carrying the ID column name as a .column_name attribute
	"""
	class TableName(ligolw.LLWNameAttr):
		dec_pattern = re.compile(r"(?:\A[a-z0-9_]+:|\A)(?P<Name>[a-z0-9_]+):table\Z")
		enc_pattern = u"%s:table"

	Name = ligolw.attributeproxy(u"Name", enc = TableName.enc, dec = TableName)

	validcolumns = None
	loadcolumns = None
	constraints = None
	how_to_index = None
	next_id = None

	class RowType(object):
		"""
		Helpful parent class for row objects.  Also used as the
		default row class by Table instances.  Provides an
		__init__() method that accepts keyword arguments from which
		the object's attributes can be initialized.

		Example:

		>>> x = Table.RowType(a = 0.0, b = "test", c = True)
		>>> x.a
		0.0
		>>> x.b
		'test'
		>>> x.c
		True

		Also provides .__getstate__() and .__setstate__() methods
		to allow row objects to be pickled (otherwise, because they
		all use __slots__ to reduce their memory footprint, they
		aren't pickleable).
		"""
		def __init__(self, **kwargs):
			for key, value in kwargs.items():
				setattr(self, key, value)

		def __getstate__(self):
			if not hasattr(self, "__slots__"):
				raise NotImplementedError
			return dict((key, getattr(self, key)) for key in self.__slots__ if hasattr(self, key))

		def __setstate__(self, state):
			self.__init__(**state)

	@property
	def columnnames(self):
		"""
		The stripped (without table prefixes attached) Name
		attributes of the Column elements in this table, in order.
		These are the names of the attributes that row objects in
		this taable possess.
		"""
		return [child.Name for child in self.getElementsByTagName(ligolw.Column.tagName)]

	@property
	def columnnamesreal(self):
		"""
		The non-stripped (with table prefixes attached) Name
		attributes of the Column elements in this table, in order.
		These are the Name attributes as they appear in the XML.
		"""
		return [child.getAttribute(u"Name") for child in self.getElementsByTagName(ligolw.Column.tagName)]

	@property
	def columntypes(self):
		"""
		The Type attributes of the Column elements in this table,
		in order.
		"""
		return [child.Type for child in self.getElementsByTagName(ligolw.Column.tagName)]

	@property
	def columnpytypes(self):
		"""
		The Python types corresponding to the Type attributes of
		the Column elements in this table, in order.
		"""
		return [ligolwtypes.ToPyType[child.Type] for child in self.getElementsByTagName(ligolw.Column.tagName)]


	#
	# Table retrieval
	#


	@classmethod
	def getTablesByName(cls, elem, name):
		"""
		Return a list of Table elements named name under elem.  See
		also .get_table().
		"""
		name = cls.TableName(name)
		return elem.getElements(lambda e: (e.tagName == cls.tagName) and (e.Name == name))

	@classmethod
	def get_table(cls, xmldoc, name = None):
		"""
		Scan xmldoc for a Table element named name.  Raises
		ValueError if not exactly 1 such table is found.  If name
		is None (default), then the .tableName attribute of this
		class is used.  The Table class does not provide a
		.tableName attribute, but sub-classes, for example those in
		lsctables.py, do provide a value for that attribute.

		The module-level get_table() function is a wrapper of this
		class method.

		Example:

		>>> from ligo.lw import ligolw
		>>> from ligo.lw import lsctables
		>>> xmldoc = ligolw.Document()
		>>> xmldoc.appendChild(ligolw.LIGO_LW()).appendChild(lsctables.New(lsctables.SnglInspiralTable))
		[]
		>>> # find table with module function
		>>> sngl_inspiral_table = get_table(xmldoc, lsctables.SnglInspiralTable.tableName)
		>>> # find table with .get_table() class method (preferred)
		>>> sngl_inspiral_table = lsctables.SnglInspiralTable.get_table(xmldoc)

		See also .getTablesByName().
		"""
		if name is None:
			name = cls.tableName
		tables = cls.getTablesByName(xmldoc, name)
		if len(tables) != 1:
			raise ValueError("document must contain exactly one %s table" % Table.TableName(name))
		return tables[0]

	def copy(self):
		"""
		Construct and return a new Table document subtree whose
		structure is the same as this table, that is it has the
		same columns etc..  The rows are not copied.  Note that a
		fair amount of metadata is shared between the original and
		new tables.  In particular, a copy of the Table object
		itself is created (but with no rows), and copies of the
		child nodes are created.  All other object references are
		shared between the two instances, such as the RowType
		attribute on the Table object.
		"""
		new = copy.copy(self)
		new.childNodes = []	# got reference to original list
		for elem in self.childNodes:
			new.appendChild(copy.copy(elem))
		del new[:]
		new._end_of_columns()
		return new


	@classmethod
	def CheckElement(cls, elem):
		"""
		Return True if element is a Table element whose Name
		attribute matches the .tableName attribute of this class ;
		return False otherwise.  See also .CheckProperties().
		"""
		return cls.CheckProperties(elem.tagName, elem.attributes)


	@classmethod
	def CheckProperties(cls, tagname, attrs):
		"""
		Return True if tagname and attrs are the XML tag name and
		element attributes, respectively, of a Table element whose
		Name attribute matches the .tableName attribute of this
		class;  return False otherwise.  The Table parent class
		does not provide a .tableName attribute, but sub-classes,
		especially those in lsctables.py, do provide a value for
		that attribute.  See also .CheckElement()

		Example:

		>>> from ligo.lw import lsctables
		>>> lsctables.ProcessTable.CheckProperties(u"Table", {u"Name": u"process:table"})
		True
		"""
		return tagname == cls.tagName and cls.TableName(attrs[u"Name"]) == cls.tableName


	#
	# Column access
	#


	def getColumnByName(self, name):
		"""
		Retrieve and return the Column child element named name.
		The comparison is done using the stripped names.  Raises
		KeyError if this table has no column by that name.

		Example:

		>>> from ligo.lw import lsctables
		>>> tbl = lsctables.New(lsctables.SnglInspiralTable)
		>>> col = tbl.getColumnByName("mass1")
		"""
		try:
			col, = Column.getColumnsByName(self, name)
		except ValueError:
			# did not find exactly 1 matching child
			raise KeyError(name)
		return col


	def appendColumn(self, name):
		"""
		Append a Column element named "name" to the table.  Returns
		the new child.  Raises ValueError if the table already has
		a column by that name, and KeyError if the validcolumns
		attribute of this table does not contain an entry for a
		column by that name.

		Example:

		>>> from ligo.lw import lsctables
		>>> tbl = lsctables.New(lsctables.ProcessParamsTable, [])
		>>> col = tbl.appendColumn("param")
		>>> print(col.getAttribute("Name"))
		param
		>>> print(col.Name)
		param
		>>> col = tbl.appendColumn(u"process:process_id")
		>>> print(col.getAttribute("Name"))
		process:process_id
		>>> print(col.Name)
		process_id
		"""
		try:
			self.getColumnByName(name)
			# if we get here the table already has that column
			raise ValueError("duplicate Column '%s'" % name)
		except KeyError:
			pass
		if name in self.validcolumns:
			coltype = self.validcolumns[name]
		elif Column.ColumnName(name) in self.validcolumns:
			coltype = self.validcolumns[Column.ColumnName(name)]
		else:
			raise ligolw.ElementError("invalid Column '%s' for Table '%s'" % (name, self.Name))
		column = Column(AttributesImpl({u"Name": u"%s" % name, u"Type": coltype}))
		streams = self.getElementsByTagName(ligolw.Stream.tagName)
		if streams:
			self.insertBefore(column, streams[0])
		else:
			self.appendChild(column)
		return column


	#
	# Row access
	#

	def appendRow(self, *args, **kwargs):
		"""
		Create and append a new row to this table, then return it

		All positional and keyword arguments are passed to the RowType
		constructor for this table.
		"""
		row = self.RowType(*args, **kwargs)
		self.append(row)
		return row


	#
	# Element methods
	#

	def _update_column_info(self):
		"""
		Deprecated stub.  Do not use.
		"""
		pass

	def _verifyChildren(self, i):
		"""
		Used for validation during parsing.  For internal use only.
		"""
		super(Table, self)._verifyChildren(i)
		child = self.childNodes[i]
		if child.tagName == ligolw.Column.tagName:
			if self.validcolumns is not None:
				if child.Name in self.validcolumns:
					expected_type = self.validcolumns[child.Name]
				elif child.getAttribute("Name") in self.validcolumns:
					expected_type = self.validcolumns[child.getAttribute("Name")]
				else:
					raise ligolw.ElementError("invalid Column '%s' for Table '%s'" % (child.Name, self.Name))
				if expected_type != child.Type:
					raise ligolw.ElementError("invalid type '%s' for Column '%s' in Table '%s', expected type '%s'" % (child.Type, child.Name, self.Name, expected_type))
			try:
				ligolwtypes.ToPyType[child.Type]
			except KeyError:
				raise ligolw.ElementError("unrecognized Type '%s' for Column '%s' in Table '%s'" % (child.Type, child.Name, self.Name))
			# since this is called after each child is
			# appeneded, the first failure occurs on the
			# offending child, so the error message reports the
			# current child as the offender
			# FIXME:  this is O(n^2 log n) in the number of
			# columns.  think about a better way
			if len(set(self.columnnames)) != len(self.columnnames):
				raise ligolw.ElementError("duplicate Column '%s' in Table '%s'" % (child.Name, self.Name))
		elif child.tagName == ligolw.Stream.tagName:
			# require agreement of non-stripped strings
			if child.getAttribute("Name") != self.getAttribute("Name"):
				raise ligolw.ElementError("Stream Name '%s' does not match Table Name '%s'" % (child.getAttribute("Name"), self.getAttribute("Name")))

	def _end_of_columns(self):
		"""
		Called during parsing to indicate that the last Column
		child element has been added.  Subclasses can override this
		to perform any special action that should occur following
		the addition of the last Column element.
		"""
		pass

	def unlink(self):
		"""
		Break internal references within the document tree rooted
		on this element to promote garbage collection.
		"""
		super(Table, self).unlink()
		del self[:]

	def endElement(self):
		# Table elements are allowed to contain 0 Stream children,
		# but _end_of_columns() hook must be called regardless, so
		# we do that here if needed.
		if self.childNodes[-1].tagName != ligolw.Stream.tagName:
			self._end_of_columns()


	#
	# Row ID manipulation
	#


	@classmethod
	def get_next_id(cls):
		"""
		Returns the current value of the next_id class attribute,
		and increments the next_id class attribute by 1.  Raises
		ValueError if the table does not have an ID generator
		associated with it.
		"""
		# = None if no ID generator
		next_id = cls.next_id
		cls.next_id += 1
		return next_id

	@classmethod
	def set_next_id(cls, next_id):
		"""
		Sets the value of the next_id class attribute.  This is a
		convenience function to help prevent accidentally assigning
		a value to an instance attribute instead of the class
		attribute.
		"""
		cls.next_id = type(cls.next_id)(next_id)

	@classmethod
	def reset_next_id(cls):
		"""
		If the current value of the next_id class attribute is not
		None then set it to 0, otherwise it is left unmodified.

		Example:

		>>> from ligo.lw import lsctables
		>>> for cls in lsctables.TableByName.values(): cls.reset_next_id()
		"""
		if cls.next_id is not None:
			cls.set_next_id(0)

	def sync_next_id(self):
		"""
		Determines the highest-numbered ID in this table, and sets
		the table's .next_id attribute to the next highest ID in
		sequence.  If the .next_id attribute is already set to a
		value greater than the highest value found, then it is left
		unmodified.  The return value is the ID identified by this
		method.  If the table's .next_id attribute is None, then
		this function is a no-op.

		Note that tables of the same name typically share a common
		.next_id attribute (it is a class attribute, not an
		attribute of each instance) so that IDs can be generated
		that are unique across all tables in the document.  Running
		sync_next_id() on all the tables in a document that are of
		the same type will have the effect of setting the ID to the
		next ID higher than any ID in any of those tables.

		Example:

		>>> from ligo.lw import lsctables
		>>> tbl = lsctables.New(lsctables.ProcessTable)
		>>> print(tbl.sync_next_id())
		0
		"""
		if self.next_id is not None:
			if len(self):
				n = max(self.getColumnByName(self.next_id.column_name)) + 1
			else:
				n = 0
			if n > self.next_id:
				self.set_next_id(n)
		return self.next_id

	def updateKeyMapping(self, mapping):
		"""
		Used as the first half of the row key reassignment
		algorithm.  Accepts a dictionary mapping old key --> new
		key.  Iterates over the rows in this table, using the
		table's next_id attribute to assign a new ID to each row,
		recording the changes in the mapping.  Returns the mapping.
		Raises ValueError if the table's next_id attribute is None.
		"""
		if self.next_id is None:
			raise ValueError(self)
		try:
			column = self.getColumnByName(self.next_id.column_name)
		except KeyError:
			# table is missing its ID column, this is a no-op
			return mapping
		table_name = self.Name
		for i, old in enumerate(column):
			if old is None:
				raise ValueError("null row ID encountered in Table '%s', row %d" % (self.Name, i))
			key = table_name, old
			if key in mapping:
				column[i] = mapping[key]
			else:
				column[i] = mapping[key] = self.get_next_id()
		return mapping

	def applyKeyMapping(self, mapping):
		"""
		Used as the second half of the key reassignment algorithm.
		Loops over each row in the table, replacing references to
		old row keys with the new values from the mapping.
		"""
		for colname in self.columnnames:
			column = self.getColumnByName(colname)
			try:
				table_name = column.table_name
			except ValueError:
				# if we get here the column's name does not
				# have a table name component, so by
				# convention it cannot contain IDs pointing
				# to other tables
				continue
			# make sure it's not our own ID column (by
			# convention this should not be possible, but it
			# doesn't hurt to check)
			if self.next_id is not None and colname == self.next_id.column_name:
				continue
			# replace IDs with new values from mapping
			for i, old in enumerate(column):
				try:
					column[i] = mapping[table_name, old]
				except KeyError:
					pass


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
	ligo.lw.ligolw.LIGOLWContentHandler, to cause it to use the Table,
	Column, and Stream classes defined in this module when parsing XML
	documents.

	Example:

	>>> from ligo.lw import ligolw
	>>> class LIGOLWContentHandler(ligolw.LIGOLWContentHandler):
	...	pass
	...
	>>> use_in(LIGOLWContentHandler)
	<class 'ligo.lw.table.LIGOLWContentHandler'>
	"""
	def startColumn(self, parent, attrs):
		return Column(attrs)

	def startStream(self, parent, attrs, __orig_startStream = ContentHandler.startStream):
		if parent.tagName == ligolw.Table.tagName:
			parent._end_of_columns()
			return TableStream(attrs).config(parent)
		return __orig_startStream(self, parent, attrs)

	def startTable(self, parent, attrs):
		return Table(attrs)

	ContentHandler.startColumn = startColumn
	ContentHandler.startStream = startStream
	ContentHandler.startTable = startTable

	return ContentHandler
