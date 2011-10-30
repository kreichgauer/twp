import collections
import struct

class Base(object):
	"""Abstract base class for TWP types."""

	def __init__(self, optional=False, name=None):
		self._optional = optional
		self._name = None

	@property
	def tag(self):
		"""The types tag."""
		raise NotImplementedError
	
	@classmethod
	def unmarshal(self, tag, value):
		"""Factory method that returns an initialized instance from a marshaled
		byte representation."""
		return self()

	def is_optional(self):
		return self._optional

	def is_empty(self):
		"""Implement to return True iff this field should not be marshalled, 
		e.g. because no meaningful value is present."""
		raise NotImplementedError

	def _marshal_tag(self):
		return chr(self.tag)

	def _marshal_value(self):
		"""Implement to return a byte string with the marshalled value."""
		raise NotImplementedError

	def _marshal_no_value(self):
		"""Implement to return a byte string with the marshalled value."""
		return NoValue().marshal()

	def marshal(self):
		if self.is_empty():
			if not self.is_optional():
				raise ValueError("Non-optional empty field.")
			return self._marshal_no_value()
		return b'%s%s' % (self._marshal_tag(), self._marshal_value())


class Primitive(Base):
	def __init__(self, value=None, **kwargs):
		super(Primitive, self).__init__(self, **kwargs)
		self.value = value

	def is_empty(self):
		return self.value is not None


class NoValueBase(Primitive):
	"""Stub for types whose instances don't have a value."""
	@property
	def value(self):
		return None

	@value.setter
	def value(self, value):
		if not value is None:
			raise ValueError("None expected as value")

	def is_empty(self):
		return False		

	@classmethod
	def unmarshal(self, tag, value):
		# FIXME ??? Allow None? Disallow ""?
		if value not in (None, ""):
			raise ValueError("No value expected.")
		return self()

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
				setattr(cls, k, None)
		return cls

	def bases_have_attr(metacls, bases, attr):
		for base in bases:
			if hasattr(base, attr):
				return True
		return False


class Complex(Base, metaclass=ComplexType):
	def __init__(self, **kwargs):
		self.update_fields(**kwargs)

	def update_fields(self, **kwargs):
		# TODO input check
		for k, v in kwargs.items():
			is_field = hasattr(self, k) and \
				isinstance(getattr(self, k), Base)
			if not is_field:
				raise ValueError("No field named %s" % k)
			setattr(self, k, v)

	def _marshal_value(self):
		marshalled = super(Complex, self).marshal()
		for name, field in self._fields.items():
			field.marshal()
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
		setattr(self, k, v)


class Struct(Complex):
	tag = 2
	# TODO implement


class Sequence(Complex):
	tag = 3
	# TODO implement


class Message(Complex):
	@property
	def identifier(self):
		"""Set to the Message's identifier, which must be in range(0,7)."""
		raise ValueError("Message without identifier.")

	@property
	def tag(self):
		"""The Message's tag. This equals 4 plus the identifier. Raises a 
		ValueError if the identifier is larger than 7."""
		if self.identifier > 7:
			raise ValueError("Message identifier cannot be greater than 7.")
		return 4 + self.identifier


class RegisteredExtension(Base):
	tag = 12
	# TODO implement


class IntegerBase(Primitive):
	format_string = None

	@classmethod
	def unmarshal(self, tag, value):
		try:
			return struct.unpack(self.format_string, value)[0]
		except struct.error:
			raise ValueError("Integer value out of bounds")

	def _marshal_value(self):
		try:
			return struct.pack(self.format_string, value)
		except struct.error:
			raise ValueError("Integer value out of bounds")		


class ShortInteger(IntegerBase):
	tag = 13
	format_string = '>b' # big endian, signed short / 1 byte


class LongInteger(IntegerBase):
	tag = 14
	format_string = '>l' # big endian, signed long / 4 bytes


class Int(Primitive):
	@classmethod
	def unmarshal(self, tag, value):
		pass


class String(Primitive):
	# TODO implement Short Strings vs. Long Strings
	tag = 127

	def _marshal_value(self):
		return self.value.decode('utf-8')
