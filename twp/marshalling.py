import struct
from twp.fields import *

def marshal_message(msg):
    return marshal_complex(msg)

def marshal_complex(field):
    if isinstance(field, AnyDefinedBy):
        # This does not quite conform to the stanard, but works for RPC.
        tag = _marshal_tag(Struct.tag)
    else:
        tag = _marshal_tag(field.tag)
    values = field.get_values()
    bytes = [marshal_value(val) for val in values]
    return tag + b"".join(bytes)

def marshal_field(field):
    val = field.value
    if isinstance(val, list):
        # We cannot have dicts here... ordering of keys
        return marshal_complex(field)
    elif isinstance(val, int):
        return marshal_int(val)
    elif isinstance(val, str):
        return marshal_str(val)
    elif isinstance(val, bytes):
        return marshal_binary(val)

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
        tag = bytes([Binary.SHORT_TAG])
        length = struct.pack("!B", length)
    elif length < 2**32:
        tag = bytes([Binary.LONG_TAG])
        length = struct.pack("!I", length)
    else:
        raise ValueError("value too long")
    return tag + length + value

def _marshal_tag(tag):
    return struct.pack("!B", tag)
