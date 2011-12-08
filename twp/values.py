# FIXME rename this module

import collections
import copy
import struct
from .error import TWPError

class Base(object):
	# FIXME find a better class name
	"""Abstract base class for TWP types."""
	tag = None

	def __init__(self, optional=False, name=None):
		self._optional = optional
		self.name = name

	@property
	def tag(self):
		"""The types tag."""
		raise NotImplementedError
	
	def _unmarshal(self, tag, value):
		raise NotImplementedError

	def unmarshal(self, data):
		# FIXME handle NoValue
		tag = data[0]
		value = data[1:]
		if not self.__class__.handles_tag(tag):
			raise TWPError("Invalid tag %d" % tag)
		unmarshalled, length = self._unmarshal(tag, value)
		self.value = unmarshalled
		length += 1
		return unmarshalled, length

	def is_optional(self):
		return self._optional

	def is_empty(self):
		"""Implement to return True iff this field should not be marshalled, 
		e.g. because no meaningful value is present."""
		raise NotImplementedError

	def _marshal_tag(self):
		"""Returns a byte string containing the tag value."""
		return bytes([self.tag])

	def _marshal_value(self):
		"""Implement to return a byte string with the marshalled value."""
		raise NotImplementedError

	def _marshal_no_value(self):
		return NoValue().marshal()

	def marshal(self):
		"""Concats `_marshal_tag()` and `_marshal_value()` if `is_empty()` 
		returns False. Otherwise, a NoValue is marshalled if the instace is
		optional, a ValueError is raised else."""
		if self.is_empty():
			if not self.is_optional():
				raise ValueError("Non-optional empty field.")
			return self._marshal_no_value()
		return self._marshal_tag() + self._marshal_value()

	@classmethod
	def handles_tag(cls, tag):
		"""Implement to return True iff the class should be used for 
		unmarshalling a field with the given tag."""
		return not tag is None and cls.tag == tag


class NoValueBase(Base):
	"""Stub for Primitives whose instances don't have a value."""
	def is_empty(self):
		return False

	def _unmarshal(self, tag, value):
		return None, 0

	def _marshal_value(self):
		return b""


class EndOfContent(NoValueBase):
	tag = 0


class NoValue(NoValueBase):
	tag = 1


class ComplexType(type):
	"""Metaclass for all Complex classes."""
	@classmethod
	def __prepare__(metacls, name, bases, **kwargs):
		# Use an OrderedDict as __dict__, so that the marshaling order of 
		# Message fields is the order in which they have been declared.
		return collections.OrderedDict()

	def __new__(metacls, name, bases, attrs):
		cls = type.__new__(metacls, name, bases, attrs)
		cls._fields = collections.OrderedDict()
		# Copy all Field-type attributes to _fields and initialize the original 
		# attributes with None.
		for k, v in attrs.items():
			if isinstance(v, Base):
				if metacls.bases_have_attr(bases, k):
					raise ValueError("%s.%s overrides a member of a base class."
						% (cls.__name__, k))
				cls._fields[k] = v
				v.name = v.name or k
				delattr(cls, k)
		return cls

	def bases_have_attr(bases, attr):
		for base in bases:
			if hasattr(base, attr):
				return True
		return False


class Complex(Base, metaclass=ComplexType):
	def __new__(cls, **kwargs):
		instance = super(Complex, cls).__new__(cls)
		# Copy all the fields to be per instance, even if defined per class
		# This is a strange way of achieving this. Better have types.Foo() 
		# return a class/factory instead and create the instances in __new__
		instance._fields = copy.deepcopy(cls._fields)
		return instance

	def __init__(self, **kwargs):
		self.update_fields(**kwargs)

	def _unmarshal(self, tag, value):
		attrs = {}
		total_length = 0
		# Marhal value field for field
		for field in instance._fields.values():
			if not len(value):
				# Value too short, wait for more input
				raise ValueError()
			unmarshalled, length = field.unmarshal(value)
			value = value[length:]
			total_length += length
			attrs[field.name] = unmarshalled
		return attrs, total_length

	def update_fields(self, **kwargs):
		# TODO input check
		for k, v in kwargs.items():
			is_field = isinstance(self._fields.get(k), Base)
			if not is_field:
				raise ValueError("No field named %s" % k)
			setattr(self, k, v)

	def get_fields(self):
		return list(self._fields.values())

	def _marshal_value(self):
		marshalled_fields = [field.marshal() for field in self._fields.values()]
		marshalled = b"".join(marshalled_fields)
		# TODO extensions?
		marshalled += EndOfContent().marshal()
		return marshalled

	def is_empty(self):
		for name, field in self._fields.items():
			if not field.is_optional() and not field.is_empty():
				return False
		return True

	def __setattr__(self, k, v):
		field = self._fields.get(k)
		if not field is None:
			field.value = v
		else:
			super(Complex, self).__setattr__(k, v)
	
	def __getattr__(self, k):
		field = self._fields.get(k)
		if field is None:
			raise AttributeError()
		return field.value


class Struct(Complex):
	tag = 2

	@staticmethod
	def with_fields(**kwargs):
		"""Returns an instance of Struct with the fields given in kwargs."""
		# This is needed, because Structs can sometimes occur without having a 
		# template class that defines all the fields. Maybe Message this is 
		# needed for Message as well.
		struct = Struct()
		for name, field in kwargs.items():
			struct._add_field(name, field)
		return struct

	def _add_field(self, name, field):
		if name in self._fields:
			raise ValueError("Struct already contains a field with this name")
		self._fields[name] = field
		field.name = field.name or name



class Sequence(Complex):
	tag = 3
	# TODO implement


class Message(Complex):
	@property
	def tag(self):
		"""The Message's tag. This equals 4 plus the identifier. Raises a 
		ValueError if the identifier is larger than 7."""
		if self.identifier > 7:
			raise ValueError("Message identifier cannot be greater than 7.")
		return self.identifier + 4

	@classmethod
	def handles_tag(cls, tag):
		"""Implement to return True iff the class should be used for 
		unmarshalling a field with the given tag."""
		return tag == cls.identifier + 4

	@property
	def _eoc(self):
		if not hasattr(self, '__eoc'):
			self.__eoc = EndOfContent()
		return self.__eoc

	def get_fields(self):
		fields = super(Message, self).get_fields()
		fields.append(self._eoc)
		return fields


class Union(Complex):
	# TODO implement
	pass


class RegisteredExtension(Complex):
	tag = 12

	@property
	def registered_id(self):
		"""Implement to return the extension's registered ID."""
		raise NotImplementedError

	def _marshal_registered_id(self):
		return struct.pack("!I", self.registered_id)

	def _marshal_value(self):
		id = self._marshal_registered_id()
		fields = super(RegisteredExtension, self)._marshal_value()
		return id + fields


class Primitive(Base):
	"""Abstract class for primitive types, i.e. types with a scalar value."""
	def __init__(self, value=None, **kwargs):
		super(Primitive, self).__init__(**kwargs)
		self.value = value

	def is_empty(self):
		return self.value is None


class Int(Primitive):
	_formats = {
		# tag, length, format
		13: (1, '>b'),
		14: (4, '>l'),
	}

	def _unpack_with_format(self, format, value):
		return struct.unpack(format, value)[0]

	def _unmarshal(self, tag, value):
		length = len(value)
		struct_length, format = self._formats[tag]
		if length < struct_length:
			raise ValueError("Invalid tag length pair (%d, %d)" % tag, length)
		unmarshalled = value[:struct_length]
		unmarshalled = self._unpack_with_format(format, unmarshalled)
		return unmarshalled, struct_length

	def _pack_with_format(self, format):
		return struct.pack(format, self.value)

	def marshal(self):
		for tag, (length, format) in self._formats.items():
			try:
				value = self._pack_with_format(format)
				tag = bytes([tag])
				return b"".join([tag, value])
			except struct.error:
				pass
		raise ValueError("Integer value out of bounds")	
		
	@classmethod	
	def handles_tag(cls, tag):
		all_tags = [t for t, (l, f) in cls._formats.items()]
		return tag in all_tags


class String(Primitive):
	SHORT_TAG = 17
	LONG_TAG = 127
	MAX_SHORT_LENGTH = 109
	MAX_LENGTH = 2**32-1

	def _unmarshal(self, tag, value):
		if tag >= self.LONG_TAG:
			return self._unmarshal_long(tag, value)
		length = tag - self.SHORT_TAG
		byte_length = len(value)
		if byte_length < length:
			raise ValueError("Value too short")
		unmarshalled = value[:length]
		try:
			unmarshalled = unmarshalled.decode('utf-8')
		except UnicodeDecodeError:
			raise TWPError("Cannot decode string")
		return unmarshalled, length

	def _unmarshal_long(self, tag, value):
		length = value[0:3]
		value = value[4:]
		try:
			length = struct.unpack("!I", length)
		except struct.error:
			raise TWPError("Cannot unpack length")
		if len(value) < length:
			raise ValueError("Value too short")
		unmarshalled = value[:length]
		try:
			unmarshalled = unmarshalled.decode('utf-8')
		except UnicodeDecodeError:
			raise TWPError("Cannot decode string")
		length += 4
		return unmarshalled, length

	def encoded_value(self):
		return self.value.encode('utf-8')

	@property
	def tag(self):
		if self.is_long_string():
			return self.LONG_TAG
		else:
			return self.SHORT_TAG + len(self.encoded_value())

	def is_long_string(self):
		return len(self.encoded_value()) > 109

	@classmethod
	def handles_tag(cls, tag):
		return tag in range(17,128)

	def _marshal_value(self):
		if self.is_long_string():
			return self._marshal_long_value()
		else:
			return self.encoded_value()

	def _marshal_long_value(self):
		value = self.encoded_value()
		if len(value) > self.MAX_LENGTH:
			raise ValueError("Value too long for long string encoding.")
		length = struct.pack('>I', len(value))
		return length + value


class MessageError(RegisteredExtension):
	registered_id = 8
	failed_msg_typs = Int() # TODO The purpose of this field is unclear...
	error_text = String()
