import struct
import twp

class Double(twp.fields.Base):
    tag = 160

    @staticmethod
    def unmarshal(self, bytes):
        try:
            return struct.unpack("!d", bytes)
        except struct.error:
            raise TWPError("Failed to decode Double from %s" % value)


class Expression(twp.values.Struct):
    host = twp.values.Binary()
    port = twp.values.Int()
    arguments = Parameters()

class Term(twp.values.Union):
    cases = {
        0: Double(),
        1: Expression(),
    }

class Parameters(twp.values.Sequence):
    type = Term()

class Request(twp.values.Message):
    id = 0
    request_id = twp.values.Int()
    arguments = Parameters()

class Reply(twp.values.Message):
    id = 1
    request_id = twp.values.Int()
    result = Double()

class Error(twp.values.Message):
    id = 2
    text = twp.values.String()

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
