import twp

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

    def __init__(self):
    	self.request_id = 0

    def request(self, operation, parameters=None, response_expected=True):
    	parameters = self.build_parameters(parameters)
    	request = Request(request_id, response_expected, operation, parameters)
    	self.send(req)
    	reply = None
    	if response_expected:
    		reply = self.recv_messages()[0]
    		if not isinstance(msg, Reply):
    			raise TWPError("Reply expected")
    	return reply


    def build_parameters(self, values):
    	pass
