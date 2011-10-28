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
	def unmarshal(self, value):
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
	def unmarshal(self, value):
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


class MessageType(BaseType):
	identifier = None

	@property
	def tag(self):
		if self.identifier > 7:
			raise ValueError("Message identifier cannot be greater than 7.")
		return 4 + self.identifier

	# TODO implement: parameters, unmarshal, marshal, ...


class RegisteredExtension(BaseType):
	tag = 12

	# TODO implement


class Integer(BaseType):
	format_string = None

	@classmethod
	def unmarshal(self, value):
		try:
			return struct.unpack(self.format_string, value)[0]
		except struct.error:
			raise ValueError("Integer value out of bounds")

	def marshal(self):
		try:
			return struct.pack(self.format_string, value)
		except struct.error:
			raise ValueError("Integer value out of bounds")		


class ShortInteger(IntegerType):
	tag = 13
	format_string = '>b' # big endian, signed short / 1 byte


class LongInteger(IntegerType):
	tag = 14
	format_string = '>l' # big endian, signed long / 4 bytes


builtin_types = [
	EndOfContentType,
	NoValueType,
	StructType,
	SequenceType,
	RegisteredExtensionType,
	ShortIntegerType,
	LongIntegerType,
	# TODO extend...
]
