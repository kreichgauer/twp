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
    def __init__(self, protocol, name, interface, result, response_expected=True):
        self.protocol = protocol
        self.name = name
        self.interface = interface
        self.result = result
        self.response_expected = response_expected

    def get_parameter_struct(self):
        params = copy.deepcopy(self.interface)
        params_struct = twp.values.Struct.with_fields(*params)
        return params_struct

    def get_result_value(self):
        return copy.deepcopy(self.result)

    def call(self, *args):
        params = self.get_parameter_struct()
        params.update_fields(*args)
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

    def __init__(self, *args, **kwargs):
        super(RPCClient, self).__init__(*args, **kwargs)
        self.request_id = 0

    @property
    def interface(self):
        """Define a mapping of method-name -> (parameter sequence, return value)
        Note that this implementation supports only in-parameters, and 0 or 1
        result values."""
        raise NotImplementedError("No interface defined")

    def define_any_defined_by(self, field, reference_value):
        assert(field.name == "parameters")
        return self.get_params(reference_value)

    def get_params(self, operation):
        operation = getattr(self, operation)
        if not isinstance(RPCMethod, operation):
            raise TWPError("No such method %s" % operation)
        return operation.build_parameter_struct()

    def request(self, operation, parameters, response_expected=True):
        request = self._build_request(response_expected, operation, parameters)
        self.send_message(request)
        reply = None
        if response_expected:
            reply = self.recv_messages()[0]
            if not isinstance(msg, Reply):
                raise TWPError("Reply expected")
        return reply

    def _build_request(self, response_expected, operation, parameters):
        id = self._get_request_id()
        response_expected = int(response_expected)
        request = Request(id, response_expected, operation, parameters)
        return request

    def _get_request_id(self):
        id = self.request_id
        self.request_id += 1
        return id
