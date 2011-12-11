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

    @property
    def interface(self):
        """Define a mapping of method-name -> (parameter sequence, return value)
        Note that this implementation supports only in-parameters, and 0 or 1
        result values."""
        raise NotImplementedError("No interface defined")

    def unmarshal_any_defined_by(self, message, field, data):
        self._unmarshal_method_parameters(message, field, data)

    def _unmarshal_method_parameters(self, message, field, data):
        assert(field.name == "parameters")
        assert(field.reference_name == "operation")
        # Get the corresponding parameter list from `self.interfaces`
        defined_by_field = message._fields[field.reference_name]
        operation = defined_by_field.value
        assert(operation) # Method name must have been given
        # Unmarshal method parameters into Struct and put into `parameters` value
        params_struct = self._build_parameter_struct(operation)
        field.value = params_struct
        return params_struct.unmarshal(data)

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

    def _build_parameter_struct(self, operation):
        params = self.interface[operation][0]
        params_struct = twp.values.Struct.with_fields(*params)
        return params_struct

    def _get_request_id(self):
        id = self.request_id
        self.request_id += 1
        return id
