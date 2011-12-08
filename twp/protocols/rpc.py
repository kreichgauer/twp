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

    def request(self, operation, parameters=None, response_expected=True):
        request = self._build_request(operation, parameters, response_expected)
        self.send(request)
        reply = None
        if response_expected:
            reply = self.recv_messages()[0]
            if not isinstance(msg, Reply):
                raise TWPError("Reply expected")
        return reply

    def _build_request(self, operation, parameters, response_expected):
        parameters = self._build_parameters(parameters)
        id = self._get_request_id()
        request = Request(id, response_expected, operation, parameters)
        return request

    def _build_parameters(self, parameters):
        param_struct = twp.values.Struct.with_fields(**parameters)
        return param_struct

    def _get_request_id(self):
        id = self.request_id
        self.request_id += 1
        return id
