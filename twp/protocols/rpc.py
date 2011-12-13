from collections import OrderedDict
import copy
import twp.values
import twp.protocol

class Request(twp.values.Message):
    id = 0
    request_id = twp.values.Int()
    response_expected = twp.values.Int()
    operation = twp.values.String()
    parameters = twp.values.AnyDefinedBy("operation")

class Reply(twp.values.Message):
    id = 1
    request_id = twp.values.Int()
    result = twp.values.AnyDefinedBy("request_id")

class CancelRequest(twp.values.Message):
    id = 2
    request_id = twp.values.Int()

class CloseConnection(twp.values.Message):
    id = 4

class RPCException(twp.values.Struct):
    extension_id = 3
    text = twp.values.String()

class RPCMethod(object):
    def __init__(self, name, interface, result, response_expected=True):
        self.name = name
        self.interface = interface
        self.result = result
        self.response_expected = response_expected
    
    def visit(self, protocol):
        self.protocol = protocol
        if hasattr(self.protocol, self.name):
            raise TypeError("Protocol already has attribute %s" % self.name)
        setattr(self.protocol, self.name, self)

    def get_parameter_struct(self):
        params = copy.deepcopy(self.interface)
        params_struct = twp.values.Struct.with_fields(name="parameters", *params)
        return params_struct

    def get_result_value(self):
        return copy.deepcopy(self.result)

    def call(self, **params):
        self.protocol.request(self.name, params, self.response_expected)

    def __call__(self, *args, **kwargs):
        self.call(*args, **kwargs)

class RPCClient(twp.protocol.TWPClient):
    protocol_id = 1
    message_types = [
        Request,
        Reply,
        CancelRequest,
        CloseConnection,
    ]
    methods = []

    def __init__(self, *args, **kwargs):
        super(RPCClient, self).__init__(*args, **kwargs)
        self.request_id = 0
        self._init_methods()

    def _init_methods(self):
        for method in self.methods:
            method.visit(self)

    def define_any_defined_by(self, field, reference_value):
        assert(field.name == "parameters")
        return self.get_params(reference_value)

    def get_params(self, operation):
        operation = getattr(self, operation)
        if not isinstance(operation, RPCMethod):
            raise TWPError("No such method %s" % operation)
        return operation.get_parameter_struct()

    def request(self, operation, parameters, response_expected=True):
        request = self._build_request(response_expected, operation, parameters)
        self.send_message(request)
        reply = None
        if response_expected:
            # FIXME check request_id
            reply = self.recv_messages()[0]
            if not isinstance(msg, Reply):
                raise TWPError("Reply expected")
        return reply

    def _build_request(self, response_expected, operation, parameters):
        id = self._get_request_id()
        response_expected = int(response_expected)
        request = Request(request_id=id, response_expected=response_expected, 
            operation=operation, parameters=parameters)
        return request

    def _get_request_id(self):
        id = self.request_id
        self.request_id += 1
        return id
