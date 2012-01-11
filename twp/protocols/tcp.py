import struct
import twp
import twp.fields
import twp.message
import twp.protocol
import twp.error

class Double(twp.fields.Primitive):
    tag = 160

    @staticmethod
    def unmarshal(bytes):
        try:
            return struct.unpack("!d", bytes)
        except struct.error:
            raise TWPError("Failed to decode Double from %s" % value)

    def marshal(self):
        try:
            return struct.pack("!Bd", self.tag, self.value)
        except struct.error:
            raise twp.error.TWPError("Failed to encode Double from %s" % self.value)


class _ForwardTerm(twp.fields.Base):
    # Abstract to twp.fields
    def __init__(self):
        self._ref = None

    @property
    def ref(self):
        if not self._ref:
            self._ref = Term()
        return self._ref

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.ref
    
    @property
    def value(self):
        return self.ref.value

    @value.setter
    def value(self, val):
        self.ref.value = val


class Parameters(twp.fields.Sequence):
    type = _ForwardTerm()

class Expression(twp.fields.Struct):
    host = twp.fields.Binary()
    port = twp.fields.Int()
    arguments = Parameters()

class Term(twp.fields.Union):
    cases = {
        0: Double(),
        1: Expression(),
    }

class Request(twp.message.Message):
    id = 0
    request_id = twp.fields.Int()
    arguments = Parameters()

class Reply(twp.message.Message):
    id = 1
    request_id = twp.fields.Int()
    result = Double()

class Error(twp.message.Message):
    id = 2
    text = twp.fields.String()

class CalculatorProtocol(twp.protocol.Protocol):
    protocol_id = 5
    message_types = [
        Request,
        Reply,
        Error,
    ]

    def read_application_type(self, tag):
        """Hook for implementing application types in Protocols."""
        if tag != 8:
            raise TWPError("Tag not understood %d" % tag)
        reader = self.connection.reader
        length = reader.read_bytes(1)
        try:
            length = struct.unpack("!B", length)
        except struct.error:
            pass
        if length != 8:
            raise TWPError("Expected 8 for Double length byte, got %s" % length)
        value = reader.read_bytes(8)
        return Double.unmarshal(value)


class OperatorImplementation(twp.protocol.TWPConsumer):
    pass
