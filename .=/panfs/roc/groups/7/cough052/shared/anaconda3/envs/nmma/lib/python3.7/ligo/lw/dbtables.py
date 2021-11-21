# Copyright (C) 2007-2018  Kipp Cannon
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
This module provides an implementation of the Table element that uses a
database engine for storage.  On top of that it then re-implements a number
of the tables from the lsctables module to provide versions of their
methods that work against the SQL database.
"""


import itertools
import operator
import os
import re
import shutil
import signal
import sys
import tempfile
import threading
from xml.sax.xmlreader import AttributesImpl
import warnings


from . import __author__, __date__, __version__
from . import ligolw
from . import table
from . import lsctables
from . import types as ligolwtypes
from . import utils as ligolw_utils


#
# =============================================================================
#
#                                  Connection
#
# =============================================================================
#


def connection_db_type(connection):
	"""
	A totally broken attempt to determine what type of database a
	connection object is attached to.  Don't use this.

	The input is a DB API 2.0 compliant connection object, the return
	value is one of the strings "sqlite3" or "mysql".  Raises TypeError
	when the database type cannot be determined.
	"""
	if "sqlite" in repr(connection):
		return "sqlite"
	if "mysql" in repr(connection):
		return "mysql"
	raise TypeError(connection)


#
# work with database file in scratch space
#


class workingcopy(object):
	"""
	Manage a working copy of an sqlite database file.  This is used
	when a large enough number of manipulations are being performed on
	a database file that the total network I/O would be higher than
	that of copying the entire file to a local disk, doing the
	manipulations locally, then copying the file back.  It is also
	useful in unburdening a file server when large numbers of read-only
	operations are being performed on the same file by many different
	machines.
	"""

	def __init__(self, filename, tmp_path = None, replace_file = False, discard = False, verbose = False):
		"""
		filename:  the name of the sqlite database file.

		tmp_path:  the directory to use for the working copy.  If
		None (the default), the system's default location for
		temporary files is used.  If set to the special value
		"_CONDOR_SCRATCH_DIR" then the value of the environment
		variable of that name will be used (to use a directory
		literally named _CONDOR_SCRATCH_DIR set tmp_path to
		"./_CONDOR_SCRATCH_DIR").

		replace_file:  if True, filename is truncated in place
		before manipulation;  if False (the default), the file is
		not modified before use.  This is used when the original
		file is being over-written with the working copy, and it is
		necessary to ensure that a malfunction or crash (which
		might prevent the working copy from over writing the
		original) does not leave behind the unmodified original,
		which could subsequently be mistaken for valid output.

		discard:  if True the working copy is simply deleted
		instead of being copied back to the original location;  if
		False (the default) the working copy overwrites the
		original.  This is used to improve read-only operations,
		when it is not necessary to pay the I/O cost of moving an
		unmodified file a second time.  The .discard attribute can
		be set at any time while the context manager is in use,
		before the .__exit__() method is invoked.

		verbose:  print messages to stderr.

		NOTES:

		- When replace_file mode is enabled, any failures that
		  prevent the original file from being trucated are
		  ignored.  The inability to truncate the file is
		  considered non-fatal.

		- If the operation to copy the file to the working path
		  fails then a working copy is not used, the original file
		  is used in place.  If the failure that prevents copying
		  the file to the working path is potentially transient,
		  for example "permission denied" or "no space on device",
		  the code sleeps for a brief period of time and then tries
		  again.  Only after the potentially transient failure
		  persists for several attempts is the working copy
		  abandoned and the original copy used instead.

		- When the working copy is moved back to the original
		  location, if a file with the same name but ending in
		  -journal is present in the working directory then it is
		  deleted.

		- The name of the working copy can be obtained by
		  converting the workingcopy object to a string.
		"""
		self.filename = filename
		self.tmp_path = tmp_path if tmp_path != "_CONDOR_SCRATCH_DIR" else os.getenv("_CONDOR_SCRATCH_DIR")
		self.replace_file = replace_file
		self.discard = discard
		self.verbose = verbose


	@staticmethod
	def truncate(filename, verbose = False):
		"""
		Truncate a file to 0 size, ignoring all errors.  This is
		used internally to implement the "replace_file" feature.
		"""
		if verbose:
			sys.stderr.write("'%s' exists, truncating ... " % filename)
		try:
			fd = os.open(filename, os.O_WRONLY | os.O_TRUNC)
		except Exception as e:
			if verbose:
				sys.stderr.write("cannot truncate '%s': %s\n" % (filename, str(e)))
			return
		os.close(fd)
		if verbose:
			sys.stderr.write("done.\n")


	@staticmethod
	def cpy(srcname, dstname, attempts = 5, verbose = False):
		"""
		Copy a file to a destination preserving permission if
		possible.  If the operation fails for a non-fatal reason
		then several attempts are made with a pause between each.
		The return value is dstname if the operation was successful
		or srcname if a non-fatal failure caused the operation to
		terminate.  Fatal failures raise an exeption.
		"""
		if verbose:
			sys.stderr.write("copying '%s' to '%s' ... " % (srcname, dstname))
		for i in itertools.count(1):
			try:
				shutil.copy2(srcname, dstname)
				# if we get here it worked
				break
			except IOError as e:
				# anything other than out-of-space is a
				# real error
				import errno
				import time
				if e.errno not in (errno.EPERM, errno.ENOSPC):
					raise
				if verbose:
					sys.stderr.write("warning: attempt %d: %s: \r" % (i, errno.errorcode[e.errno]))
				# if we've run out of attempts, fall back
				# to the original file
				if i > 4:
					if verbose:
						sys.stderr.write("working with original file '%s'\n" % srcname)
					return srcname
				# otherwise sleep and try again
				if verbose:
					sys.stderr.write("sleeping and trying again ...\n")
				time.sleep(10)
		if verbose:
			sys.stderr.write("done.\n")
		try:
			# try to preserve permission bits.  according to
			# the documentation, copy() and copy2() are
			# supposed preserve them but don't.  maybe they
			# don't preserve them if the destination file
			# already exists?
			shutil.copystat(srcname, dstname)
		except Exception as e:
			if verbose:
				sys.stderr.write("warning: ignoring failure to copy permission bits from '%s' to '%s': %s\n" % (srcname, dstname, str(e)))
		return dstname


	def __enter__(self):
		database_exists = os.access(self.filename, os.F_OK)

		if self.tmp_path is not None:
			# create the remporary file and retain a reference
			# to prevent its removal.  for suffix, can't use
			# splitext() because it only keeps the last bit,
			# e.g. won't give ".xml.gz" but just ".gz"

			self.temporary_file = tempfile.NamedTemporaryFile(suffix = ".".join(os.path.split(self.filename)[-1].split(".")[1:]), dir = self.tmp_path)
			self.target = self.temporary_file.name
			if self.verbose:
				sys.stderr.write("using '%s' as workspace\n" % self.target)

			# mkstemp() ignores umask, creates all files accessible
			# only by owner;  we should respect umask.  note that
			# os.umask() sets it, too, so we have to set it back after
			# we know what it is

			umsk = os.umask(0o777)
			os.umask(umsk)
			os.chmod(self.target, 0o666 & ~umsk)

			if database_exists:
				# if the file is being replaced then
				# truncate the database so that if this job
				# fails the user won't think the database
				# file is valid, otherwise copy the
				# existing database to the work space for
				# modification
				if self.replace_file:
					self.truncate(self.filename, verbose = self.verbose)
				elif self.cpy(self.filename, self.target, verbose = self.verbose) == self.filename:
					# non-fatal errors have caused us
					# to fall-back to the file in its
					# original location
					self.target = self.filename
					del self.temporary_file
		else:
			self.target = self.filename
			if database_exists and self.replace_file:
				self.truncate(self.target, verbose = self.verbose)

		return self


	def __str__(self):
		return self.target


	def __exit__(self, exc_type, exc_val, exc_tb):
		"""
		Restore the working copy to its original location if the
		two are different.

		During the move operation, this function traps the signals
		used by Condor to evict jobs.  This reduces the risk of
		corrupting a document by the job terminating part-way
		through the restoration of the file to its original
		location.  When the move operation is concluded, the
		original signal handlers are restored and if any signals
		were trapped they are resent to the current process in
		order.  Typically this will result in the signal handlers
		installed by the install_signal_trap() function being
		invoked, meaning any other scratch files that might be in
		use get deleted and the current process is terminated.
		"""
		# when removed, must also delete a -journal partner, ignore
		# all errors

		try:
			orig_unlink("%s-journal" % self)
		except:
			pass

		# restore the file to its original location

		if self.target != self.filename:
			with ligolw_utils.SignalsTrap():
				if not self.discard:
					# move back to original location

					if self.verbose:
						sys.stderr.write("moving '%s' to '%s' ... " % (self.target, self.filename))
					shutil.move(self.target, self.filename)
					if self.verbose:
						sys.stderr.write("done.\n")

					# next we will trigger the
					# temporary file removal.  because
					# we've just deleted that file,
					# this will produce an annoying but
					# harmless message about an ignored
					# OSError.  so silence the warning
					# we create a dummy file for the
					# TemporaryFile to delete.  ignore
					# any errors that occur when trying
					# to make the dummy file.  FIXME:
					# this is stupid, find a better way
					# to shut TemporaryFile up

					try:
						open(self.target, "w").close()
					except:
						pass

				# remove reference to
				# tempfile.TemporaryFile object.  this
				# triggers the removal of the file.

				del self.temporary_file

		# if an exception terminated the code block, re-raise the
		# exception

		return False


	def set_temp_store_directory(self, connection, verbose = False):
		"""
		Sets the temp_store_directory parameter in sqlite.
		"""
		if verbose:
			sys.stderr.write("setting the temp_store_directory to %s ... " % self.tmp_path)
		cursor = connection.cursor()
		cursor.execute("PRAGMA temp_store_directory = '%s'" % self.tmp_path)
		cursor.close()
		if verbose:
			sys.stderr.write("done\n")


#
# backwards compatibility for old code.  FIXME:  delete in next release
#


def get_connection_filename(*args, **kwargs):
	return workingcopy(*args, **kwargs).__enter__()


def put_connection_filename(ignored, target, verbose = False):
	target.verbose = verbose
	target.__exit__(None, None, None)

def discard_connection_filename(ignored, target, verbose = False):
	target.discard = True
	target.verbose = verbose
	target.__exit__(None, None, None)

def set_temp_store_directory(connection, temp_store_directory, verbose = False):
	if temp_store_directory == "_CONDOR_SCRATCH_DIR":
		temp_store_directory = os.getenv("_CONDOR_SCRATCH_DIR")
	if verbose:
		sys.stderr.write("setting the temp_store_directory to %s ... " % temp_store_directory)
	cursor = connection.cursor()
	cursor.execute("PRAGMA temp_store_directory = '%s'" % temp_store_directory)
	cursor.close()
	if verbose:
		sys.stderr.write("done\n")


#
# =============================================================================
#
#                                  ID Mapping
#
# =============================================================================
#


def idmap_create(connection):
	"""
	Create the _idmap_ table.  This table has columns "table_name",
	"old", and "new" mapping old IDs to new IDs for each table.  The
	(table_name, old) column pair is a primary key (is indexed and must
	contain unique entries).  The table is created as a temporary
	table, so it will be automatically dropped when the database
	connection is closed.

	This function is for internal use, it forms part of the code used
	to re-map row IDs when merging multiple documents.
	"""
	connection.cursor().execute("CREATE TEMPORARY TABLE _idmap_ (table_name TEXT NOT NULL, old INTEGER NOT NULL, new INTEGER NOT NULL, PRIMARY KEY (table_name, old))")


def idmap_reset(connection):
	"""
	Erase the contents of the _idmap_ table, but leave the table in
	place.

	This function is for internal use, it forms part of the code used
	to re-map row IDs when merging multiple documents.
	"""
	connection.cursor().execute("DELETE FROM _idmap_")


def idmap_sync(connection):
	"""
	Iterate over the tables in the database, ensure that there exists a
	custom DBTable class for each, and synchronize that table's ID
	generator to the ID values in the database.
	"""
	xmldoc = get_xml(connection)
	for tbl in xmldoc.getElementsByTagName(DBTable.tagName):
		tbl.sync_next_id()
	xmldoc.unlink()


def idmap_get_new(cursor, table_name, old, tbl):
	"""
	From the old ID string, obtain a replacement ID string by either
	grabbing it from the _idmap_ table if one has already been assigned
	to the old ID, or by using the current value of the Table
	instance's next_id class attribute.  In the latter case, the new ID
	is recorded in the _idmap_ table, and the class attribute
	incremented by 1.

	This function is for internal use, it forms part of the code used
	to re-map row IDs when merging multiple documents.
	"""
	cursor.execute("SELECT new FROM _idmap_ WHERE table_name == ? AND old == ?", (table_name, old))
	new = cursor.fetchone()
	if new is not None:
		# a new ID has already been created for this old ID
		return new[0]
	# this ID was not found in _idmap_ table, assign a new ID and
	# record it
	new = tbl.get_next_id()
	cursor.execute("INSERT INTO _idmap_ VALUES (?, ?, ?)", (table_name, old, new))
	return new


#
# =============================================================================
#
#                             Database Information
#
# =============================================================================
#


#
# SQL parsing
#


_sql_create_table_pattern = re.compile(r"CREATE\s+TABLE\s+(?P<name>\w+)\s*\((?P<coldefs>.*)\)", re.IGNORECASE)
_sql_coldef_pattern = re.compile(r"\s*(?P<name>\w+)\s+(?P<type>\w+)[^,]*")


#
# Database info extraction utils
#


def get_table_names(connection):
	"""
	Return a list of the table names in the database.
	"""
	cursor = connection.cursor()
	cursor.execute("SELECT name FROM sqlite_master WHERE type == 'table'")
	return [name for (name,) in cursor]


def get_column_info(connection, table_name):
	"""
	Return an in order list of (name, type) tuples describing the
	columns in the given table.
	"""
	cursor = connection.cursor()
	cursor.execute("SELECT sql FROM sqlite_master WHERE type == 'table' AND name == ?", (table_name,))
	statement, = cursor.fetchone()
	coldefs = re.match(_sql_create_table_pattern, statement).groupdict()["coldefs"]
	return [(coldef.groupdict()["name"], coldef.groupdict()["type"]) for coldef in re.finditer(_sql_coldef_pattern, coldefs) if coldef.groupdict()["name"].upper() not in ("PRIMARY", "UNIQUE", "CHECK")]


def get_xml(connection, table_names = None):
	"""
	Construct an XML document tree wrapping around the contents of the
	database.  On success the return value is a ligolw.LIGO_LW element
	containing the tables as children.  Arguments are a connection to
	to a database, and an optional list of table names to dump.  If
	table_names is not provided the set is obtained from get_table_names()
	"""
	ligo_lw = ligolw.LIGO_LW()

	if table_names is None:
		table_names = get_table_names(connection)

	for table_name in table_names:
		# build the table document tree.  copied from
		# lsctables.New()
		try:
			cls = TableByName[table_name]
		except KeyError:
			cls = DBTable
		table_elem = cls(AttributesImpl({u"Name": u"%s:table" % table_name}), connection = connection)
		destrip = {}
		if table_elem.validcolumns is not None:
			for name in table_elem.validcolumns:
				destrip[table.Column.ColumnName(name)] = name
		for column_name, column_type in get_column_info(connection, table_elem.Name):
			if table_elem.validcolumns is not None:
				try:
					column_name = destrip[column_name]
				except KeyError:
					raise ValueError("invalid column")
				# use the pre-defined column type
				column_type = table_elem.validcolumns[column_name]
			else:
				# guess the column type
				column_type = ligolwtypes.FromSQLiteType[column_type]
			table_elem.appendChild(table.Column(AttributesImpl({u"Name": column_name, u"Type": column_type})))
		table_elem._end_of_columns()
		table_elem.appendChild(table.TableStream(AttributesImpl({u"Name": u"%s:table" % table_name, u"Delimiter": table.TableStream.Delimiter.default, u"Type": table.TableStream.Type.default})))
		ligo_lw.appendChild(table_elem)
	return ligo_lw


#
# =============================================================================
#
#                            DBTable Element Class
#
# =============================================================================
#


# FIXME:  is this needed?
class DBTableStream(table.TableStream):
	def endElement(self):
		super(DBTableStream, self).endElement()
		if hasattr(self.parentNode, "connection"):
			self.parentNode.connection.commit()


class DBTable(table.Table):
	"""
	A version of the Table class using an SQL database for storage.
	Many of the features of the Table class are not available here, but
	instead the user can use SQL to query the table's contents.

	The constraints attribute can be set to a text string that will be
	added to the table's CREATE statement where constraints go, for
	example you might wish to set this to "PRIMARY KEY (event_id)" for
	a table with an event_id column.

	Note:  because the table is stored in an SQL database, the use of
	this class imposes the restriction that table names be unique
	within a document.

	Also note that at the present time there is really only proper
	support for the pre-defined tables in the lsctables module.  It is
	possible to load unrecognized tables into a database from LIGO
	Light Weight XML files, but without developer intervention there is
	no way to indicate the constraints that should be imposed on the
	columns, for example which columns should be used as primary keys
	and so on.  This can result in poor query performance.  It is also
	possible to extract a database' contents to a LIGO Light Weight XML
	file even when the database contains unrecognized tables, but
	without developer intervention the column types will be guessed
	using a generic mapping of SQL types to LIGO Light Weight types.

	Each instance of this class must be connected to a database.  The
	(Python DBAPI 2.0 compatible) connection object is passed to the
	class via the connection parameter at instance creation time.

	Example:

	>>> import sqlite3
	>>> connection = sqlite3.connection()
	>>> tbl = dbtables.DBTable(AttributesImpl({u"Name": u"process:table"}), connection = connection)

	A custom content handler must be created in order to pass the
	connection keyword argument to the DBTable class when instances are
	created, since the default content handler does not do this.  See
	the use_in() function defined in this module for information on how
	to create such a content handler

	If a custom ligo.lw.Table subclass is defined in ligo.lw.lsctables
	whose name matches the name of the DBTable being constructed, the
	lsctables class is added to the list of parent classes.  This
	allows the lsctables class' methods to be used with the DBTable
	instances but not all of the methods will necessarily work with the
	database-backed version of the class.  Your mileage may vary.

	"""
	def __new__(cls, *args, **kwargs):
		# does this class already have table-specific metadata?
		if not hasattr(cls, "tableName"):
			# no, try to retrieve it from lsctables
			attrs, = args
			name = table.Table.TableName(attrs[u"Name"])
			if name in lsctables.TableByName:
				# found metadata in lsctables, construct
				# custom subclass.  the class from
				# lsctables is added as a parent class to
				# allow methods from that class to be used
				# with this class, however there is no
				# guarantee that all parent class methods
				# will be appropriate for use with the
				# DB-backend object.
				lsccls = lsctables.TableByName[name]
				class CustomDBTable(cls, lsccls):
					tableName = lsccls.tableName
					validcolumns = lsccls.validcolumns
					loadcolumns = lsccls.loadcolumns
					constraints = lsccls.constraints
					next_id = lsccls.next_id
					RowType = lsccls.RowType
					how_to_index = lsccls.how_to_index

				# save for re-use (required for ID
				# remapping across multiple documents in
				# ligolw_sqlite)
				TableByName[name] = CustomDBTable

				# replace input argument with new class
				cls = CustomDBTable
		return table.Table.__new__(cls, *args)

	def __init__(self, *args, **kwargs):
		# chain to parent class
		table.Table.__init__(self, *args)

		# retrieve connection object from kwargs
		self.connection = kwargs.pop("connection")

		# pre-allocate a cursor for internal queries
		self.cursor = self.connection.cursor()

	def copy(self, *args, **kwargs):
		"""
		This method is not implemented.  See ligo.lw.table.Table
		for more information.
		"""
		raise NotImplementedError

	def _end_of_columns(self):
		table.Table._end_of_columns(self)
		# dbcolumnnames and types have the "not loaded" columns
		# removed
		if self.loadcolumns is not None:
			self.dbcolumnnames = [name for name in self.columnnames if name in self.loadcolumns]
			self.dbcolumntypes = [name for i, name in enumerate(self.columntypes) if self.columnnames[i] in self.loadcolumns]
		else:
			self.dbcolumnnames = self.columnnames
			self.dbcolumntypes = self.columntypes

		# create the table
		ToSQLType = {
			"sqlite": ligolwtypes.ToSQLiteType,
			"mysql": ligolwtypes.ToMySQLType
		}[connection_db_type(self.connection)]
		try:
			statement = "CREATE TABLE IF NOT EXISTS " + self.Name + " (" + ", ".join(map(lambda n, t: "%s %s" % (n, ToSQLType[t]), self.dbcolumnnames, self.dbcolumntypes))
		except KeyError as e:
			raise ValueError("column type '%s' not supported" % str(e))
		if self.constraints is not None:
			statement += ", " + self.constraints
		statement += ")"
		self.cursor.execute(statement)

		# row ID where remapping is to start
		self.remap_first_rowid = None

		# construct the SQL to be used to insert new rows
		params = {
			"sqlite": ",".join("?" * len(self.dbcolumnnames)),
			"mysql": ",".join(["%s"] * len(self.dbcolumnnames))
		}[connection_db_type(self.connection)]
		self.append_statement = "INSERT INTO %s (%s) VALUES (%s)" % (self.Name, ",".join(self.dbcolumnnames), params)
		self.append_attrgetter = operator.attrgetter(*self.dbcolumnnames)

	def sync_next_id(self):
		if self.next_id is not None:
			maxid = self.cursor.execute("SELECT MAX(%s) FROM %s" % (self.next_id.column_name, self.Name)).fetchone()[0]
			if maxid is not None:
				# type conversion not needed for
				# .set_next_id(), but needed so we can do
				# arithmetic on the thing
				maxid = type(self.next_id)(maxid) + 1
				if maxid > self.next_id:
					self.set_next_id(maxid)
		return self.next_id

	def maxrowid(self):
		self.cursor.execute("SELECT MAX(ROWID) FROM %s" % self.Name)
		return self.cursor.fetchone()[0]

	def __len__(self):
		self.cursor.execute("SELECT COUNT(*) FROM %s" % self.Name)
		return self.cursor.fetchone()[0]

	def __iter__(self):
		cursor = self.connection.cursor()
		cursor.execute("SELECT * FROM %s ORDER BY rowid ASC" % self.Name)
		for values in cursor:
			yield self.row_from_cols(values)

	def __reversed__(self):
		cursor = self.connection.cursor()
		cursor.execute("SELECT * FROM %s ORDER BY rowid DESC" % self.Name)
		for values in cursor:
			yield self.row_from_cols(values)

	# FIXME:  is adding this a good idea?
	#def __delslice__(self, i, j):
	#	# sqlite numbers rows starting from 1:  [0:10] becomes
	#	# "rowid between 1 and 10" which means 1 <= rowid <= 10,
	#	# which is the intended range
	#	self.cursor.execute("DELETE FROM %s WHERE ROWID BETWEEN %d AND %d" % (self.Name, i + 1, j))

	def _append(self, row):
		"""
		Standard .append() method.  This method is for intended for
		internal use only.
		"""
		self.cursor.execute(self.append_statement, self.append_attrgetter(row))

	def _remapping_append(self, row):
		"""
		Replacement for the standard .append() method.  This
		version performs on the fly row ID reassignment, and so
		also performs the function of the updateKeyMapping()
		method.  SQLite does not permit the PRIMARY KEY of a row to
		be modified, so it needs to be done prior to insertion.
		This method is intended for internal use only.
		"""
		if self.next_id is not None:
			# assign (and record) a new ID before inserting the
			# row to avoid collisions with existing rows
			setattr(row, self.next_id.column_name, idmap_get_new(self.cursor, self.Name, getattr(row, self.next_id.column_name), self))
		self._append(row)
		if self.remap_first_rowid is None:
			self.remap_first_rowid = self.maxrowid()
			assert self.remap_first_rowid is not None

	append = _append

	def row_from_cols(self, values):
		"""
		Given an iterable of values in the order of columns in the
		database, construct and return a row object.  This is a
		convenience function for turning the results of database
		queries into Python objects.
		"""
		row = self.RowType()
		for c, v in zip(self.dbcolumnnames, values):
			setattr(row, c, v)
		return row
	# backwards compatibility
	_row_from_cols = row_from_cols

	def unlink(self):
		table.Table.unlink(self)
		self.connection = None
		self.cursor = None

	def applyKeyMapping(self):
		"""
		Used as the second half of the key reassignment algorithm.
		Loops over each row in the table, replacing references to
		old row keys with the new values from the _idmap_ table.
		"""
		if self.remap_first_rowid is None:
			# no rows have been added since we processed this
			# table last
			return
		assignments = []
		for colname in self.dbcolumnnames:
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
			assignments.append("%s = (SELECT new FROM _idmap_ WHERE _idmap_.table_name == \"%s\" AND _idmap_.old == %s)" % (colname, table_name, colname))
		assignments = ", ".join(assignments)
		if assignments:
			# SQLite documentation says ROWID is monotonically
			# increasing starting at 1 for the first row unless
			# it ever wraps around, then it is randomly
			# assigned.  ROWID is a 64 bit integer, so the only
			# way it will wrap is if somebody sets it to a very
			# high number manually.  This library does not do
			# that, so I don't bother checking.
			self.cursor.execute("UPDATE %s SET %s WHERE ROWID >= %d" % (self.Name, assignments, self.remap_first_rowid))
		self.remap_first_rowid = None


#
# =============================================================================
#
#                                  LSC Tables
#
# =============================================================================
#


class CoincMapTable(DBTable):
	tableName = lsctables.CoincMapTable.tableName
	validcolumns = lsctables.CoincMapTable.validcolumns
	constraints = lsctables.CoincMapTable.constraints
	next_id = lsctables.CoincMapTable.next_id
	RowType = lsctables.CoincMapTable.RowType
	how_to_index = lsctables.CoincMapTable.how_to_index

	def applyKeyMapping(self):
		if self.remap_first_rowid is not None:
			self.cursor.execute("UPDATE coinc_event_map SET event_id = (SELECT new FROM _idmap_ WHERE _idmap_.table_name == coinc_event_map.table_name AND old == event_id), coinc_event_id = (SELECT new FROM _idmap_ WHERE _idmap_.table_name == 'coinc_event' AND old == coinc_event_id) WHERE ROWID >= ?", (self.remap_first_rowid,))
			self.remap_first_rowid = None


class TimeSlideTable(DBTable):
	tableName = lsctables.TimeSlideTable.tableName
	validcolumns = lsctables.TimeSlideTable.validcolumns
	constraints = lsctables.TimeSlideTable.constraints
	next_id = lsctables.TimeSlideTable.next_id
	RowType = lsctables.TimeSlideTable.RowType
	how_to_index = lsctables.TimeSlideTable.how_to_index

	def as_dict(self):
		"""
		Return a dictionary mapping time slide IDs to offset
		dictionaries.
		"""
		# import is done here to reduce risk of a cyclic
		# dependency.  at the time of writing there is not one, but
		# we can help prevent it in the future by putting this
		# here.
		from lalburst import offsetvector
		return dict((time_slide_id, offsetvector.offsetvector((instrument, offset) for time_slide_id, instrument, offset in values)) for time_slide_id, values in itertools.groupby(self.cursor.execute("SELECT time_slide_id, instrument, offset FROM time_slide ORDER BY time_slide_id"), lambda time_slide_id_instrument_offset: time_slide_id_instrument_offset[0]))

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
			raise KeyError(offsetdict)
		if len(ids) == 1:
			# found one
			return ids[0]
		# offset vector not found in table
		if create_new is None:
			# and that's not OK
			raise KeyError(offsetdict)
		# that's OK, create new vector
		time_slide_id = self.get_next_id()
		for instrument, offset in offsetdict.items():
			row = self.RowType()
			row.process_id = create_new.process_id
			row.time_slide_id = time_slide_id
			row.instrument = instrument
			row.offset = offset
			self.append(row)

		# return new ID
		return time_slide_id


#
# =============================================================================
#
#                                Table Metadata
#
# =============================================================================
#


def build_indexes(connection, verbose = False):
	"""
	Using the how_to_index annotations in the table class definitions,
	construct a set of indexes for the database at the given
	connection.
	"""
	cursor = connection.cursor()
	for table_name in get_table_names(connection):
		# FIXME:  figure out how to do this extensibly
		if table_name in TableByName:
			how_to_index = TableByName[table_name].how_to_index
		elif table_name in lsctables.TableByName:
			how_to_index = lsctables.TableByName[table_name].how_to_index
		else:
			continue
		if how_to_index is not None:
			if verbose:
				sys.stderr.write("indexing %s table ...\n" % table_name)
			for index_name, cols in how_to_index.items():
				cursor.execute("CREATE INDEX IF NOT EXISTS %s ON %s (%s)" % (index_name, table_name, ",".join(cols)))
	connection.commit()


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
	CoincMapTable.tableName: CoincMapTable,
	TimeSlideTable.tableName: TimeSlideTable
}


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
	ligo.lw.ligolw.LIGOLWContentHandler, to cause it to use the DBTable
	class defined in this module when parsing XML documents.  Instances
	of the class must provide a connection attribute.  When a document
	is parsed, the value of this attribute will be passed to the
	DBTable class' .__init__() method as each table object is created,
	and thus sets the database connection for all table objects in the
	document.

	Example:

	>>> import sqlite3
	>>> from ligo.lw import ligolw
	>>> class MyContentHandler(ligolw.LIGOLWContentHandler):
	...	def __init__(self, *args):
	...		super(MyContentHandler, self).__init__(*args)
	...		self.connection = sqlite3.connection()
	...
	>>> use_in(MyContentHandler)

	Multiple database files can be in use at once by creating a content
	handler class for each one.
	"""
	ContentHandler = lsctables.use_in(ContentHandler)

	def startStream(self, parent, attrs, __orig_startStream = ContentHandler.startStream):
		if parent.tagName == ligolw.Table.tagName:
			parent._end_of_columns()
			return DBTableStream(attrs).config(parent)
		return __orig_startStream(self, parent, attrs)

	def startTable(self, parent, attrs):
		name = table.Table.TableName(attrs[u"Name"])
		if name in TableByName:
			return TableByName[name](attrs, connection = self.connection)
		return DBTable(attrs, connection = self.connection)

	ContentHandler.startStream = startStream
	ContentHandler.startTable = startTable

	return ContentHandler
