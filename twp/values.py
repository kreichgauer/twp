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
	
	def _unmarshal(self, tag, value):
		raise NotImplementedError

	def unmarshal(self, data):
		# FIXME handle NoValue
		tag = data[0]
		value = data[1:]
		if not self.__class__.handles_tag(tag):
			raise TWPError("Invalid tag %d" % tag)
		unmarshalled, length = self._unmarshal(tag, value)
		length += 1
		return unmarshalled, length

	def is_optional(self):
		return self._optional

	def _marshal_tag(self, value):
		"""Returns a byte string containing the tag value."""
		return bytes([self.tag])

	def _marshal_value(self, value):
		"""Implement to return a byte string with the marshalled value."""
		raise NotImplementedError

	def marshal(self, value):
		"""Concats `_marshal_tag()` and `_marshal_value()` if `is_empty()` 
		returns False. Otherwise, a NoValue is marshalled if the instace is
		optional, a ValueError is raised else."""
		if value is None:
			if not self.is_optional():
				raise ValueError("Non-optional empty field %s." % self.name)
			return NoValue().marshal()
		return self._marshal_tag(value) + self._marshal_value(value)

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

	def marshal(self):
		return bytes([self.tag])


class EndOfContent(NoValueBase):
	tag = 0


class NoValue(NoValueBase):
	tag = 1


class _ComplexType(type):
	"""Metaclass for Complex classes with fields."""
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
					raise TypeError("%s.%s overrides a member of a base class."
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


class _Complex(Base, metaclass=_ComplexType):
	def _unmarshal(self, tag, value):
		unmarshalled = {}
		total_length = 0
		# Marhal value field for field
		for field in self._fields.values():
			if not len(value):
				# Value too short, wait for more input
				raise ValueError()
			val, length = self._unmarshal_field(field, value, unmarshalled)
			value = value[length:]
			total_length += length
		EndOfContent().unmarshal(value)
		value = value[1:]
		total_length += 1
		return unmarshalled, total_length

	def _unmarshal_field(self, field, value, into):
		# prev_values is the result of `unmarshal` so far. This all exists, so
		# Message can override it. Ugly as shit.
		unmarshalled, length = field.unmarshal(value)
		into[field.name] = unmarshalled
		return unmarshalled, length

	def _marshal_value(self, values):
		if len(values) != len(self._fields):
			raise TypeError("Wrong number of values (expected %d, got %d" %
				(len(values), len(self._fields)))
		marshalled_fields = []
		for name, field in self._fields.items():
			self._marshal_field(field, values, marshalled_fields)
		marshalled_fields.append(EndOfContent().marshal())
		marshalled = b"".join(marshalled_fields)
		return marshalled

	def _marshal_field(self, field, values, into):
		value = values.get(field.name)
		marshalled = field.marshal(value)
		into.append(marshalled)
		return marshalled


class Struct(_Complex):
	tag = 2

	@staticmethod
	def with_fields(*args, **kwargs):
		"""Returns an instance of Struct with the fields given in kwargs."""
		struct = Struct()
		for field in args:
			assert(field.name)
			struct._add_field(field.name, field)
		for name, field in kwargs.items():
			struct._add_field(name, field)
		return struct

	def _add_field(self, name, field):
		if name in self._fields:
			raise ValueError("Struct already contains a field with this name")
		self._fields[name] = field
		field.name = field.name or name


class Sequence(Base): # Should be Complex, but isn't
	tag = 3
	type = None

	def _marshal_value(self, values):
		marshalled = [self.type.marshal(value) for value in values]
		marshalled.append(EndOfContent().marshal())
		return b"".join(marshalled)

	def _unmarshal(self, tag, value):
		unmarshalled = []
		total_length = 0
		while value:
			if value[0] == EndOfContent.tag:
				length += 1
				return unmarshalled, total_length
			val, length = self.type.unmarshal(value)
			unmarshalled.append(val)
			value = value[length:]
			total_length += length
		# Need more bytes
		raise ValueError()


class Message(_Complex):
	def __init__(self, **values):
		self.protocol = None
		self.values = values

	@property
	def tag(self):
		"""The Message's tag. This equals 4 plus the id. Raises a 
		ValueError if the id is larger than 7."""
		if not hasattr(self, 'id'):
			raise ValueError("Message must have an id attribute.")
		if self.id > 7:
			raise ValueError("Message id cannot be greater than 7.")
		return self.id + 4

	@classmethod
	def handles_tag(cls, tag):
		"""Implement to return True iff the class should be used for 
		unmarshalling a field with the given tag."""
		return tag == cls.id + 4

	def marshal_message(self, protocol):
		# Set this, so we can ask it for the definition of AnyDefinedBy fields
		# Yes, I know this stinks.
		self.protocol = protocol
		marshalled = self.marshal(self.values)
		self.protocol = None
		return marshalled

	def _marshal_field(self, field, value, into):
		# Have Protocol resolve AnyDefinedBy fields
		if isinstance(field, AnyDefinedBy):
			reference_value = into[field.reference_name]
			field = self.protocol.define_any_defined_by(field, reference_value)
		return super(Message, self)._marshal_field(field, value, into)

	def unmarshal_message(self, data, protocol):
		self.protocol = protocol
		unmarshalled, length = self.unmarshal(data)
		self.values = unmarshalled
		self.protocol = None

	def _unmarshal_field(self, field, value, into):
		if isinstance(field, AnyDefinedBy):
			reference_value = into[field.reference_name]
			field = self.protocol.define_any_defined_by(field, reference_value)
		return super(Message, self)._unmarshal_field(field, value, into)


class Union(_Complex):
	# TODO implement
	pass


class RegisteredExtension(_Complex):
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
	pass

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

	def _pack_with_format(self, format, value):
		return struct.pack(format, value)

	def marshal(self, value):
		for tag, (length, format) in self._formats.items():
			try:
				value = self._pack_with_format(format, value)
				tag = bytes([tag])
				return b"".join([tag, value])
			except struct.error:
				pass
		raise TypeError("Integer value out of bounds")	
		
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

	def encoded_value(self, value):
		return value.encode('utf-8')

	def _marshal_tag(self, value):
		if self.is_long_string(value):
			tag = self.LONG_TAG
		else:
			tag = self.SHORT_TAG + len(self.encoded_value(value))
		return bytes([tag])

	def is_long_string(self, value):
		return len(self.encoded_value(value)) > 109

	@classmethod
	def handles_tag(cls, tag):
		return tag in range(17,128)

	def _marshal_value(self, value):
		if self.is_long_string(value):
			return self._marshal_long_value(value)
		else:
			return self.encoded_value(value)

	def _marshal_long_value(self, value):
		value = self.encoded_value(value)
		if len(value) > self.MAX_LENGTH:
			raise ValueError("Value too long for long string encoding.")
		length = struct.pack('>I', len(value))
		return length + value


class Binary(Primitive):
	pass


class AnyDefinedBy(Primitive):
	def __init__(self, reference_name, *args, **kwargs):
		super(AnyDefinedBy, self).__init__(*args, **kwargs)
		self.reference_name = reference_name

	@classmethod
	def handles_tag(cls, tag):
		return False

	def marshal(self):
		# Forward to value, which must, unfortunately, understand marshal
		return self.value.marshal()

	def unmarshal(self, data):
		# Shiiit
		tag = data[0]
		value_type = value_types.get(tag)
		if value_type is None:
			raise TWPError("Invalid tag: %s" % tag)
		return value_type.unmarshal(data)


class MessageError(RegisteredExtension):
	registered_id = 8
	failed_msg_typs = Int() # TODO The purpose of this field is unclear...
	error_text = String()
