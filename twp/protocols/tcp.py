import operator
import struct
import time
from twp import log
import twp.fields
import twp.message
import twp.protocol
import twp.protocols.logging
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

    def get_thread_id(self):
        for ext in self.extensions:
            if isinstance(ext, ThreadID):
                return ext

class Reply(twp.message.Message):
    id = 1
    request_id = twp.fields.Int()
    result = Double()

class Error(twp.message.Message):
    id = 2
    text = twp.fields.String()

class ThreadID(twp.message.Extension):
    registered_id = 42
    tid = twp.fields.Int()
    depth = twp.fields.Int()


class CalculatorProtocol(twp.protocol.Protocol):
    protocol_id = 5
    message_types = [
        Request,
        Reply,
        Error,
    ]
    extension_types = [
        ThreadID,
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

class RequestHandler():
    def __init__(self, consumer):
        self.consumer = consumer
        self.request = None
        self.operands = {}

    def get_twp_client(self, host, port):
        return twp.protocol.TWPClientAsync(host, port, 
            protocol_class = self.consumer.protocol_class,
            message_handler_func=self.handle_expression_result,
            )#error_handler_func=self.handle_expression_error)

    def handle(self, request):
        if self.request:
            raise ValueError("Already handling %s" % self.request)
        self.request = request
        for idx in range(len(request.arguments)):
            operand = request.arguments[idx]
            self.handle_operand(operand, idx)
        self.send_result_if_complete()

    def handle_operand(self, op, arg_idx):
        # op is a union value
        case, op = op
        if case == 0:
            assert(isinstance(op, float))
            self.operands[arg_idx] = op
        elif case == 1:
            self.evaluate_operand(op, arg_idx)
        else:
            self.send_error("Invalid op case?")

    def evaluate_operand(self, op, arg_idx):
        # op is an tcp.Expression value
        host, port, arguments = op
        try:
            host = twp.utils.unpack_ip(host)
        except ValueError:
            host = twp.utils.unpack_ip6(host)
        req = Request(arg_idx, arguments)
        # Forward all extensions
        self._add_request_extensions(req)
        client = self.get_twp_client(host, port)
        client.send_twp(req)

    def _add_request_extensions(self, req):
        has_tid = False
        for ext in self.request.extensions:
            if isinstance(ext, ThreadID):
                ext = ThreadID(ext.tid, ext.depth + 1)
                has_tid = True
            req.extensions.append(ext)
        if not has_tid:
            tid = ThreadID(self.request.request_id, 1)
            req.extensions.append(tid)

    def handle_expression_result(self, msg, client):
        log.warn("Result from async client %s" % msg)
        client.close()
        if not isinstance(msg, Reply):
            log.warn("Expected reply, but got: %s" % msg)
            self.send_error("Unexpected message from intermediate.")
            self.close()
            return
        rid = msg.request_id
        # TODO sanity check rid
        self.operands[rid] = msg.result
        self.send_result_if_complete()

    def handle_expression_error(self, client):
        log.warn("Error from async client")
        self.send_error("Intermediate failed to deliver result.")
        client.close()

    def send_result_if_complete(self):
        if len(self.operands) != len(self.request.arguments):
            return
        result = self.perform_operation()
        reply = Reply(self.request.request_id, result)
        log.debug("Reply for %s: %s" % (reply.request_id, reply.result))
        self.consumer.send_twp(reply)

    def perform_operation(self):
        return self.consumer.operator_function(self.operands.values())

    def send_error(self, text, close=True):
        err = Error(text)
        self.consumer.send_twp(err)
        if close:
            self.consumer.close()


class OperatorImplementation(twp.protocol.TWPConsumer):
    protocol_class = CalculatorProtocol
    operator_function = operator.add
        
    def __init__(self, *args, **kwargs):
        # TODO
        self.operator_function = kwargs.pop("op_func", self.operator_function)
        twp.protocol.TWPConsumer.__init__(self, *args, **kwargs)
        self.name = "mk %s %s" % self.getsockname()
        self._log_client = None

    def on_message(self, msg):
        log.debug("Received message %s" % msg)
        if isinstance(msg, Request):
            self.handle_request(msg)
        else:
            self.send_error("Expected a request.")

    def handle_request(self, req):
        log.debug("Received request (%s): %s " % (req.request_id, req.arguments))
        self.log_request(req)
        handler = RequestHandler(self)
        handler.handle(req)

    def get_log_client(self):
        if not self._log_client:
            self._log_client = twp.protocol.TWPClientAsync(
                'www.dcl.hpi.uni-potsdam.de', 80, 
                protocol_class=twp.protocols.logging.LoggingProtocol)
        return self._log_client

    def log_request(self, msg):
        try:
            le = twp.protocols.logging.LogEntry()
            le.seconds = int(time.time())
            le.useconds = 0
            le.source = self.name
            thread_id = msg.get_thread_id()
            if thread_id:
                le.thread_id = "%s" % thread_id._fields
            le.text = "Request %s: %s" % (msg.id, msg.arguments)
            # FIXME self.get_log_client().send_twp(le)
            log.error("Would log to service: %s" % le)
        except:
            log.warn("logging service request failed")
            raise

    def on_close(self):
        self.log_client.close()


class TCPServer(twp.protocol.TWPServer):
    def __init__(self, host, port, op_func=None):
        self.op_func = op_func
        twp.protocol.TWPServer.__init__(self, host, port, handler_class=OperatorImplementation)

    def _get_handler(self, sock, addr):
        return self.handler_class(sock, addr, op_func=self.op_func)


class TCPClient(twp.protocol.TWPClient):
    protocol_class = CalculatorProtocol
