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

	def __init__(self, name=None, *args, **kwargs):
		super(_Complex, self).__init__(name=name)
		self.update_values(*args, **kwargs)

	def update_values(self, *args, **kwargs):		
		if len(args) > len(self._fields):
			raise ValueError("Too many positional args")
		for name, value in zip(self._fields.keys(), args):
			setattr(self, name, value)
		for name, value in kwargs.items():
			if not name in self._fields:
				raise ValueError("Unknown field name: %s" % name)
			setattr(self, name, value)

	def __getattr__(self, name):
		if name in self._fields:
			return self._fields[name].value
		raise AttributeError()

	def __setattr__(self, name, value):
		try:
			self._fields[name].value = value
		except KeyError:
			super(_Complex, self).__setattr__(name, value)

	def get_fields(self):
		"""Returns an iterable of fields in marshalling order."""
		return self._fields.values()

	@property
	def value(self):
		return self._fields

	@value.setter
	def set_value(self, values):
		# Delegate to field definitions
		try:
			self.update_values(*values)
		except TypeError:
			# Not a list, maybe a dict?
			self.update_values(**values)


class Struct(_Complex):
	tag = 2


class Sequence(Base): # Should be Complex, but isn't
	tag = 3
	type = None


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
