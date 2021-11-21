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
While the ligolw module provides classes and parser support for reading and
writing LIGO Light Weight XML documents, this module supplements that code
with classes and parsers that add intelligence to the in-RAM document
representation.

In particular, the document tree associated with an Array element is
enhanced.  During parsing, the Stream element in this module converts the
character data contained within it into the elements of a numpy array
object.  The array has the appropriate dimensions and type.  When the
document is written out again, the Stream element serializes the array back
into character data.

The array is stored as an attribute of the Array element.
"""


import itertools
import numpy
import re
import sys
from xml.sax.saxutils import escape as xmlescape
from xml.sax.xmlreader import AttributesImpl as Attributes


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


def get_array(xmldoc, name):
	"""
	Scan xmldoc for an array named name.  Raises ValueError if not
	exactly 1 such array is found.
	"""
	arrays = Array.getArraysByName(xmldoc, name)
	if len(arrays) != 1:
		raise ValueError("document must contain exactly one %s array" % Array.ArrayName(name))
	return arrays[0]


#
# =============================================================================
#
#                               Element Classes
#
# =============================================================================
#


class ArrayStream(ligolw.Stream):
	"""
	High-level Stream element for use inside Arrays.  This element
	knows how to parse the delimited character stream into the parent's
	array attribute, and knows how to turn the parent's array attribute
	back into a character stream.
	"""

	Delimiter = ligolw.attributeproxy(u"Delimiter", default = u" ")

	def __init__(self, *args):
		super(ArrayStream, self).__init__(*args)
		try:
			self.Encoding
		except AttributeError:
			pass
		else:
			raise ligolw.ElementError("non-default encoding '%s' not supported.  if this is critical, please report." % self.Encoding)
		self._tokenizer = tokenizer.Tokenizer(self.Delimiter)

	def config(self, parentNode):
		# some initialization that can only be done once parentNode
		# has been set.
		self._tokenizer.set_types([ligolwtypes.ToPyType[parentNode.Type]])
		parentNode.array = numpy.zeros(parentNode.shape, ligolwtypes.ToNumPyType[parentNode.Type])
		self._array_view = parentNode.array.T.flat
		self._index = 0
		return self

	def appendData(self, content):
		# tokenize buffer, and assign to array
		tokens = tuple(self._tokenizer.append(content))
		next_index = self._index + len(tokens)
		self._array_view[self._index : next_index] = tokens
		self._index = next_index

	def endElement(self):
		# stream tokenizer uses delimiter to identify end of each
		# token, so add a final delimiter to induce the last token
		# to get parsed.
		self.appendData(self.Delimiter)
		if self._index != len(self._array_view):
			raise ValueError("length of Stream (%d elements) does not match array size (%d elements)" % (self._index, len(self._array_view)))
		del self._array_view
		del self._index

	def write(self, fileobj = sys.stdout, indent = u""):
		# avoid symbol and attribute look-ups in inner loop
		w = fileobj.write
		w(self.start_tag(indent))

		array = self.parentNode.array
		if array is not None:
			# avoid symbol and attribute look-ups in inner
			# loop.  we use self.parentNode.shape to retrieve
			# the array's shape, rather than just asking the
			# array, to induce a sanity check that the Dim
			# elements are correct for the array
			linelen = self.parentNode.shape[0]
			lines = array.size // linelen if array.size else 0
			tokens = iter(map(ligolwtypes.FormatFunc[self.parentNode.Type], array.T.flat))
			islice = itertools.islice
			join = self.Delimiter.join

			if lines:
				newline = u"\n" + indent + ligolw.Indent
				w(newline)
				w(xmlescape(join(islice(tokens, linelen))))
				newline = self.Delimiter + newline
				for i in range(lines - 1):
					w(newline)
					w(xmlescape(join(islice(tokens, linelen))))
		w(u"\n" + self.end_tag(indent) + u"\n")


class Array(ligolw.Array):
	"""
	High-level Array element.

	Examples:

	>>> import numpy
	>>> x = numpy.mgrid[0:5,0:3][0]
	>>> x
	array([[0, 0, 0],
	       [1, 1, 1],
	       [2, 2, 2],
	       [3, 3, 3],
	       [4, 4, 4]])
	>>> x.shape
	(5, 3)
	>>> elem = Array.build("test", x, ["dim0", "dim1"])
	>>> elem.shape
	(5, 3)
	>>> import sys
	>>> elem.write(sys.stdout)	# doctest: +NORMALIZE_WHITESPACE
	<Array Type="int_8s" Name="test:array">
		<Dim Name="dim1">3</Dim>
		<Dim Name="dim0">5</Dim>
		<Stream Type="Local" Delimiter=" ">
			0 1 2 3 4
			0 1 2 3 4
			0 1 2 3 4
		</Stream>
	</Array>
	>>> # change the Array shape.  the internal array is changed, too
	>>> elem.shape = 15
	>>> elem.write(sys.stdout)	# doctest: +NORMALIZE_WHITESPACE
	<Array Type="int_8s" Name="test:array">
		<Dim Name="dim0">15</Dim>
		<Stream Type="Local" Delimiter=" ">
			0 0 0 1 1 1 2 2 2 3 3 3 4 4 4
		</Stream>
	</Array>
	>>> # replace the internal array with one with a different number
	>>> # of dimensions.  assign to .array first, then fix .shape
	>>> elem.array = numpy.mgrid[0:4,0:3,0:2][0]
	>>> elem.shape = elem.array.shape
	>>> elem.write(sys.stdout)	# doctest: +NORMALIZE_WHITESPACE
	<Array Type="int_8s" Name="test:array">
		<Dim>2</Dim>
		<Dim>3</Dim>
		<Dim Name="dim0">4</Dim>
		<Stream Type="Local" Delimiter=" ">
			0 1 2 3
			0 1 2 3
			0 1 2 3
			0 1 2 3
			0 1 2 3
			0 1 2 3
		</Stream>
	</Array>
	"""
	class ArrayName(ligolw.LLWNameAttr):
		dec_pattern = re.compile(r"(?P<Name>[a-zA-Z0-9_:]+):array\Z")
		enc_pattern = u"%s:array"

	Name = ligolw.attributeproxy(u"Name", enc = ArrayName.enc, dec = ArrayName)

	def __init__(self, *args):
		"""
		Initialize a new Array element.
		"""
		super(Array, self).__init__(*args)
		self.array = None

	@property
	def shape(self):
		"""
		The Array's dimensions.  If the shape described by the Dim
		child elements is not consistent with the shape of the
		internal array object then ValueError is raised.

		When assigning to this property, the internal array object
		is adjusted as well, and an error will be raised if the
		re-shape is not allowed (see numpy documentation for the
		rules).  If the number of dimensions is being changed, and
		the Array object requires additional Dim child elements to
		be added, they are created with higher ranks than the
		existing dimensions, with no Name attributes assigned;
		likewise if Dim elements need to be removed, the highest
		rank dimensions are removed first.  NOTE: Dim elements are
		stored in reverse order, so the highest rank dimension
		corresponds to the first Dim element in the XML tree.

		NOTE:  the shape of the internal numpy array and the shape
		described by the Dim child elements are only weakly related
		to one another.  There are some sanity checks watching out
		for inconsistencies, for example when retrieving the value
		of this property, or when writing the XML tree to a file,
		but in general there is no mechanism preventing
		sufficiently quirky code from getting the .array attribute
		out of sync with the Dim child elements.  Calling code
		should ensure it contains its own safety checks where
		needed.
		"""
		shape = tuple(c.n for c in self.getElementsByTagName(ligolw.Dim.tagName))[::-1]
		if self.array is not None and self.array.shape != shape:
			raise ValueError("shape of Dim children not consistent with shape of .array:  %s != %s" % (str(shape), str(self.array.shape)))
		return shape

	@shape.setter
	def shape(self, shape):
		# adjust the internal array.  this has the side effect of
		# testing that the new shape is permitted
		if self.array is not None:
			self.array.shape = shape

		# make sure we have the correct number of Dim elements.
		# Dim elements are in the reverse order relative to the
		# entries in shape, so we remove extra ones or add extra
		# ones at the start of the list to preseve the metadata of
		# the lower-indexed dimensions
		dims = self.getElementsByTagName(ligolw.Dim.tagName)
		try:
			len(shape)
		except TypeError:
			shape = (shape,)
		while len(dims) > len(shape):
			self.removeChild(dims.pop(0)).unlink()
		while len(dims) < len(shape):
			if dims:
				# prepend new Dim elements
				dim = self.insertBefore(ligolw.Dim(), dims[0])
			elif self.childNodes:
				# there are no Dim children, only other
				# allowed child is a single Stream, and
				# Dim children must come before it
				assert len(self.childNodes) == 1 and self.childNodes[-1].tagName == ligolw.Stream.tagName, "invalid children"
				dim = self.insertBefore(ligolw.Dim(), self.childNodes[-1])
			else:
				dim = self.appendChild(ligolw.Dim())
			dims.insert(0, dim)

		# set the dimension sizes of the Dim elements
		for dim, n in zip(dims, reversed(shape)):
			dim.n = n

	@classmethod
	def build(cls, name, array, dim_names = None):
		"""
		Construct a LIGO Light Weight XML Array document subtree
		from a numpy array object.

		Example:

		>>> import numpy, sys
		>>> a = numpy.arange(12, dtype = "double")
		>>> a.shape = (4, 3)
		>>> Array.build(u"test", a).write(sys.stdout)	# doctest: +NORMALIZE_WHITESPACE
		<Array Type="real_8" Name="test:array">
			<Dim>3</Dim>
			<Dim>4</Dim>
			<Stream Type="Local" Delimiter=" ">
				0 3 6 9
				1 4 7 10
				2 5 8 11
			</Stream>
		</Array>
		"""
		# Type must be set for .__init__();  easier to set Name
		# afterwards to take advantage of encoding handled by
		# attribute proxy
		self = cls(Attributes({u"Type": ligolwtypes.FromNumPyType[str(array.dtype)]}))
		self.Name = name
		self.shape = array.shape
		if dim_names is not None:
			if len(dim_names) != len(array.shape):
				raise ValueError("dim_names must be same length as number of dimensions")
			for child, name in zip(self.getElementsByTagName(ligolw.Dim.tagName), reversed(dim_names)):
				child.Name = name
		self.appendChild(ArrayStream(Attributes({u"Type": ArrayStream.Type.default, u"Delimiter": ArrayStream.Delimiter.default})))
		self.array = array
		return self

	@classmethod
	def getArraysByName(cls, elem, name):
		"""
		Return a list of arrays with name name under elem.
		"""
		name = cls.ArrayName(name)
		return elem.getElements(lambda e: (e.tagName == cls.tagName) and (e.Name == name))

	#
	# Element methods
	#

	def unlink(self):
		"""
		Break internal references within the document tree rooted
		on this element to promote garbage collection.
		"""
		super(Array, self).unlink()
		self.array = None


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
	ligo.lw.ligolw.LIGOLWContentHandler, to cause it to use the Array
	and ArrayStream classes defined in this module when parsing XML
	documents.

	Example:

	>>> from ligo.lw import ligolw
	>>> class MyContentHandler(ligolw.LIGOLWContentHandler):
	...	pass
	...
	>>> use_in(MyContentHandler)
	<class 'ligo.lw.array.MyContentHandler'>
	"""
	def startStream(self, parent, attrs, __orig_startStream = ContentHandler.startStream):
		if parent.tagName == ligolw.Array.tagName:
			return ArrayStream(attrs).config(parent)
		return __orig_startStream(self, parent, attrs)

	def startArray(self, parent, attrs):
		return Array(attrs)

	ContentHandler.startStream = startStream
	ContentHandler.startArray = startArray

	return ContentHandler
