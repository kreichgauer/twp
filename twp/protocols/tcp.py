import struct
from twp import log
import twp.fields
import twp.message
import twp.protocol
import twp.error
import twp.utils

class Double(twp.fields.Primitive):
    tag = 160
    _length = 8

    @staticmethod
    def unmarshal(bytes):
        try:
            return struct.unpack("!d", bytes)[0]
        except struct.error:
            raise twp.error.TWPError("Failed to decode Double from %s" % value)

    def marshal(self):
        try:
            return struct.pack("!BBd", self.tag, self._length, self.value)
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
        if tag != 160:
            raise twp.error.TWPError("Tag not understood %d" % tag)
        reader = self.connection.reader
        length = reader.read_bytes(1)[0]
        if length != 8:
            raise twp.error.TWPError("Expected 8 for Double length byte, got %s" % length)
        value = reader.read_bytes(8)
        return Double.unmarshal(value)


class OperatorImplementation(twp.protocol.TWPConsumer):
    protocol_class = CalculatorProtocol
        
    def __init__(self, *args, **kwargs):
        twp.protocol.TWPConsumer.__init__(self, *args, **kwargs)
        self.request = None
        self.operands = {}

    def get_twp_client(self, host, port):
        return twp.protocol.TWPClientAsync(host, port, 
            protocol_class = self.protocol_class,
            message_handler_func=self.handle_expression_result)

    def on_message(self, msg):
        if isinstance(msg, Request):
            self.handle_request(msg)
        else:
            self.send_error("Expected a request.")

    def handle_request(self, req):
        log.debug("Received request (%s): %s " % (req.request_id, req.arguments))
        self.request = req
        for i in range(len(req.arguments)):
            operand = req.arguments[i]
            self.handle_operand(operand, i)
        self.send_result_if_complete()

    def handle_operand(self, op, i):
        # op is a union value
        case, op = op
        if case == 0:
            assert(isinstance(op, float))
            self.operands[i] = op
        elif case == 1:
            self.evaluate_operand(op, i)
        else:
            self.send_error("Invalid op case?")

    def evaluate_operand(self, op, i):
        # op is an tcp.Expression value
        host, port, arguments = op
        try:
            host = twp.utils.unpack_ip(host)
        except ValueError:
            host = twp.utils.unpack_ip6(host)
        req = Request(i, arguments)
        client = self.get_twp_client(host, port)
        client.send_twp(req)

    def handle_expression_result(self, msg, client):
        client.close()
        if not isinstance(msg, Reply):
            # TODO send error to *our* client
            self.close()
            return
        rid = msg.request_id
        # TODO sanity check rid
        self.operands[rid] = msg.result
        self.send_result_if_complete()

    def send_result_if_complete(self):
        if len(self.operands) != len(self.request.arguments):
            return
        result = self.perform_operation()
        reply = Reply(self.request.request_id, result)
        log.debug("Reply for %s: %s" % (reply.request_id, reply.result))
        self.send_twp(reply)

    def perform_operation(self):
        return sum(self.operands.values())

    def send_error(self, text, close=True):
        err = Error(text)
        self.send_twp(err)
        if close:
            self.close()


class TCPClient(twp.protocol.TWPClient):
    protocol_class = CalculatorProtocol
