import struct

class BaseType(object):
	"""Abstract base class for TWP types."""

	@property
	def tag(self):
		"""The types tag."""
		raise NotImplementedError

	def decode(self, value):
		raise NotImplementedError

	def encode(self, value):
		return chr(self.tag) + value


class EndOfContentType(BaseType):
	tag = 0

	def decode(self, value):
		# FIXME ??? Allow None? Disallow ""?
		if val != "":
			raise ValueError("No value expected.")
		return val

	def encode(self, value):
		if val != ""
			raise ValueError("No value expected.")
		return super(EndOfContentType, self).encode(value)


class NoValueType(BaseType):
	tag = 0

	def decode(self, value):
		if val != "":
			raise ValueError("No value expected.")
		return val

	def encode(self, value):
		if val != ""
			raise ValueError("No value expected.")
		return super(NoValueType, self).encode(value)


class StructType(BaseType):
	tag = 2

	# TODO implement


class SequenceType(BaseType):
	tag = 3

	# TODO implement


class MessageType(BaseType):
	identifier = None

	@property
	def tag(self):
		if self.identifier > 7:
			raise ValueError("Message identifier cannot be greater than 7.")
		return 4 + self.identifier

	# TODO implement: parameters, decode, encode, ...


class RegisteredExtensionType(BaseType):
	tag = 12

	# TODO implement


class IntegerType(BaseType):
	format_string = None

	def decode(self, value):
		try:
			return struct.unpack(self.format_string, value)[0]
		except struct.error:
			raise ValueError("Integer value out of bounds")

	def encode(self, value):
		try:
			return struct.pack(self.format_string, value)
		except struct.error:
			raise ValueError("Integer value out of bounds")		


class ShortIntegerType(IntegerType):
	tag = 13
	format_string = '>b' # big endian, signed short / 1 byte


class LongIntegerType(IntegerType):
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
