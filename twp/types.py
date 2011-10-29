import struct

class BaseType(object):
	"""Abstract base class for TWP types."""

	def __init__(self):
		self.value = None

	def __init__(self, value):
		self.value = value

	@property
	def tag(self):
		"""The types tag."""
		raise NotImplementedError
	
	@classmethod
	def unmarshal(self, tag, value):
		"""Factory method that returns an initialized instance from a marshaled
		byte representation."""
		return self()

	def marshal(self):
		return chr(self.tag) + value


class EmptyType(BaseType):
	"""Stub for types whose instances don't have a value."""
	
	def __init__(self, value):
		raise ValueError("No value expected.")

	@classmethod
	def unmarshal(self, tag, value):
		# FIXME ??? Allow None? Disallow ""?
		if value not in (None, ""):
			raise ValueError("No value expected.")
		return self()

	def marshal(self):
		if not self.value is None:
			raise ValueError("No value expected.")
		return super(EmptyType, self).marshal("")


class EndOfContent(EmptyType):
	tag = 0


class NoValue(EmptyType):
	tag = 1


class Struct(BaseType):
	tag = 2
	# TODO implement


class Sequence(BaseType):
	tag = 3
	# TODO implement


class Field(BaseType):
	def __init__(self, type, name=None, optional=False):
		self.type = type
		self.name = name
		self.optional = optional

	def unmarshal():
		pass


class MessageBase(type):

	def __init__(cls, name, bases, attrs):
		cls._fields = dict()
		# TODO Raise if any of the Fields override superclass attributes
		for k, v in attrs.iteritems():
			if isinstance(v, Field):
				cls._fields[k] = v
				v.name = v.name or k
				setattr(cls, k, None)
		return type.__init__(cls, name, bases, attrs)


class Message(EmptyType):
	__metaclass__ = MessageBase
	identifier = None

	def __init__(self, **kwargs):
		self.update_fields(**kwargs)

	def update_fields(self, **kwargs):
		# TODO input check
		for k, v in kwargs.iteritems():
			setattr(self, k, v)

	@property
	def tag(self):
		if self.identifier > 7:
			raise ValueError("Message identifier cannot be greater than 7.")
		return 4 + self.identifier

	def marshal(self):
		marshalled = super(Message, self).marshal()
		for type_, name, optional in self.fields_descr:
			field = self.fields[name]
			marshalled += field.marshal()
		marshalled += EndOfContent().marshal()
		return marshalled


class RegisteredExtension(BaseType):
	tag = 12
	# TODO implement


class IntegerBase(BaseType):
	format_string = None

	@classmethod
	def unmarshal(self, tag, value):
		try:
			return struct.unpack(self.format_string, value)[0]
		except struct.error:
			raise ValueError("Integer value out of bounds")

	def marshal(self):
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


class Int(BaseType):
	@classmethod
	def unmarshal(self, tag, value):
		pass


class String(BaseType):
	pass


builtin_types = [
	EndOfContent,
	NoValue,
	Struct,
	Sequence,
	RegisteredExtension,
	ShortInteger,
	LongInteger,
	# TODO extend...
]
