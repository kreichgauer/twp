import struct
from twp.fields import *
from twp.message import Message, Extension

EOC = b"\0"
NO_VAL = b"\1"

def marshal(val):
    """Marshal anything that can be sent over a connection, i.e. Message, 
    Extension, or primitive value."""
    if isinstance(val, Message):
        return _marshal_complex(val)
    elif isinstance(val, Extension):
        return marshal_extension(val)
    else:
        return marshal_value(val)

def _marshal_field(field):
    if isinstance(field, Primitive):
        return marshal_value(field.value)
    elif isinstance(field, Struct):
        return _marshal_complex(field)
    elif isinstance(field, Sequence):
        return _marshal_sequence(field)
    elif isinstance(field, Union):
        raise NotImplementedError()
    elif isinstance(field, AnyDefinedBy):
        return _marshal_any_defined_by(field)
    else:
        raise ValueError("Not a supported field %s" % field)

def _marshal_complex(complex):
    """Marshals an instance of `twp.fields.Complex`"""
    tag = _marshal_tag(complex.tag)
    values = [_marshal_field(field) for field in complex.get_fields()]
    return tag + b"".join(values) + EOC

def _marshal_sequence(sequence):
    type_field = sequence.type
    values = []
    for val in sequence.value:
        type_field.value = val
        values.append(_marshal_field(type_field))
    type_field.value = None
    tag = _marshal_tag(sequence.tag)
    return tag + b"".join(values) + EOC

def _marshal_any_defined_by(field):
    val = field.value
    # Not quite as per standard, but works for our RPC use cases at least.
    if isinstance(val, list):
        tag = _marshal_tag(Struct.tag)
        values = [marshal_value(val) for v in val]
        return tag + b"".join() + EOC
    else:
        return marshal_value(val)

def marshal_value(val):
    """Marshals a primitive python value"""
    if isinstance(val, int):
        return marshal_int(val)
    elif isinstance(val, str):
        return marshal_str(val)
    elif isinstance(val, bytes):
        return marshal_binary(val)
    elif val is None:
        return NO_VAL
    else:
        raise ValueError("Cannot marshal %s" % val)

def marshal_int(value):
    value = int(value)
    for tag, format in Int.formats.items():
        try:
            value = struct.pack(format, value)
            tag = _marshal_tag(tag)
            return tag + value
        except struct.error:
            pass
    raise ValueError("Integer value out of bounds %s" % value)

def marshal_str(value):
    value = str(value).encode("utf-8")
    length = len(value)
    if length <= String.MAX_SHORT_LENGTH:
        tag = _marshal_tag(String.SHORT_TAG + length)
    elif length <= String.MAX_LENGTH:
        tag = _marshal_tag(String.LONG_TAG)
        tag += struct.pack("!I", length)
    else:
        raise ValueError("String too long")
    return tag + value

def marshal_binary(value):
    value = bytes(value)
    length = len(value)
    if length < 256:
        tag = _marshal_tag(Binary.SHORT_TAG)
        length = struct.pack("!B", length)
    elif length < 2**32:
        tag = _marshal_tag  (Binary.LONG_TAG)
        length = struct.pack("!I", length)
    else:
        raise ValueError("value too long")
    return tag + length + value

def marshal_no_value(value):
    return _marshal_tag(1)

def _marshal_tag(tag):
    assert(tag < 256)
    return bytes([tag])
