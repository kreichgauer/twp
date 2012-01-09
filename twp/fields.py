# FIXME rename this module

import collections
import copy
import struct
from .error import TWPError

class Base(object):
	"""Abstract base class for TWP types."""
	tag = None

	def __init__(self, name=None):
		self.name = name


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
	def __new__(cls, *args, **kwargs):
		instance = super(_Complex, cls).__new__(cls)
		# Copy all the fields to be per instance, even if defined per class
		# This is a strange way of achieving this. Better have types.Foo() 
		# return a class/factory instead and create the instances in __new__
		instance._fields = copy.deepcopy(cls._fields)
		return instance


class Struct(_Complex):
	tag = 2

	@classmethod
	def with_fields(cls, *args, name=None, **kwargs):
		"""Returns an instance of Struct with the fields given in kwargs."""
		struct = cls(name=name)
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
				total_length += 1
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

	def _marshal_field(self, field, values, into):
		# Have Protocol resolve AnyDefinedBy fields
		if isinstance(field, AnyDefinedBy):
			reference_value = values[field.reference_name]
			field = self.protocol.define_any_defined_by(field, reference_value)
		return super(Message, self)._marshal_field(field, values, into)

	def unmarshal_message(self, data, protocol):
		self.protocol = protocol
		unmarshalled, length = self.unmarshal(data)
		self.values = unmarshalled
		self.protocol = None
		return unmarshalled, length

	def _unmarshal_field(self, field, value, into):
		if isinstance(field, AnyDefinedBy):
			reference_value = into[field.reference_name]
			field = self.protocol.define_any_defined_by(field, reference_value)
		return super(Message, self)._unmarshal_field(field, value, into)

	def __repr__(self):
		return "%s: %s" % (self.__class__, self.values)


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
	def __init__(self, *args, **kwargs):
		super(Primitive, self).__init__(*args, **kwargs)
		self.value = None


class Int(Primitive):
	formats = {
		13: "!b",
		14: "!i",
	}


class String(Primitive):
	SHORT_TAG = 17
	LONG_TAG = 127
	MAX_SHORT_LENGTH = 109
	MAX_LENGTH = 2**32-1


class Binary(Primitive):
	SHORT_TAG = 15
	LONG_TAG = 16


class AnyDefinedBy(Primitive):
	def __init__(self, reference_name, *args, **kwargs):
		super(AnyDefinedBy, self).__init__(*args, **kwargs)
		self.reference_name = reference_name
