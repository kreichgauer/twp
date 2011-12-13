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
    
    def visit(self, client):
        self.client = client
        if hasattr(self.client, self.name):
            raise TypeError("Client already has attribute %s" % self.name)
        setattr(self.client, self.name, self)

    def get_parameter_struct(self):
        if len(self.interface) == 1:
            self.interface[0].name = "parameters"
            return self.interface[0]
        params = copy.deepcopy(self.interface)
        params_struct = twp.values.Struct.with_fields(name="parameters", *params)
        return params_struct

    def get_result_struct(self):
        result = copy.deepcopy(self.result)
        if isinstance(result, twp.values.Base) or len(result) == 1:
            result.name = "result"
        else:
            result = twp.values.Struct.with_fields(name="result", *result)
        return result

    def call(self, **params):
        if len(params) == 1:
            _, params = params.popitem()
        return self.client.request(self.name, params, self.response_expected)

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)


class RPC(twp.protocol.Protocol):
    protocol_id = 1
    message_types = [
        Request,
        Reply,
        CancelRequest,
        CloseConnection,
    ]
    methods = []

    def define_any_defined_by(self, field, reference_value):
        if field.name == "parameters":
            return self.get_params(reference_value)
        elif field.name == "result":
            return self.get_results(reference_value)

    def _get_method(self, name):
        method = None
        for m in self.methods:
            if m.name == name:
                method = m
                break
        return method

    def get_params(self, operation):
        """Returns the param struct or value for the given operation name."""
        operation = self._get_method(operation)
        if not isinstance(operation, RPCMethod):
            raise TWPError("No such method %s" % operation)
        return operation.get_parameter_struct()

    def get_results(self, request_id):
        """Returns the result struct or value for the given request id."""
        # FIXME This would not work for a server.
        try:
            req = self.connection.requests[request_id]
        except KeyError:
            raise TWPError("Invalid request id.")
        operation = getattr(self.connection, req.values["operation"])
        return operation.get_result_struct()

class RPCClient(twp.protocol.TWPClient):
    def __init__(self, *args, **kwargs):
        super(RPCClient, self).__init__(*args, **kwargs)
        self.request_id = 0
        self.requests = []
        self._init_methods()

    def _init_methods(self):
        for method in self.protocol.methods:
            method.visit(self)

    def request(self, operation, parameters, response_expected=True):
        request = self._build_request(response_expected, operation, parameters)
        self.send_message(request)
        # Store request for later reference
        self.requests.append(request)
        assert(len(self.requests) == self.request_id)
        reply = None
        if response_expected:
            # FIXME check request_id
            reply = self.recv_messages()[0]
            if not isinstance(reply, Reply):
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
