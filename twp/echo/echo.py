from .. import protocol
from .. import types

class Request(types.Message):
	identifier = 0
	fields_descr = [
		(types.String, "text", False),
	]


class Response(types.Message):
	identifier = 1
	fields_descr = [
		(types.String, "text", False),
		(types.Int, "number_of_letters", False),
	]


class EchoProtocol(protocol.BaseProtocol):

	protocol_id = 2
	message_types = [
		RequestMessage,
		ResponseMessage,
	]

	def on_connect(self):
		self._send(b'\x04')
		echo_req = 'ping'
		tag = chr(17 + len(echo_req))
		self._send(b'' + tag  + echo_req)
		self._send(b'\x00')
	
	def on_data(self, data):
		log.debug('Data received: %r' % data)

	def on_end(self):
		pass
