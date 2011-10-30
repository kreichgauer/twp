from .. import protocol
from .. import types

class Request(types.Message):
	identifier = 0
	text = types.String()


class Response(types.Message):
	identifier = 1
	text = types.String()
	number_of_letters = types.Int()


class EchoProtocol(protocol.BaseProtocol):

	protocol_id = 2
	message_types = [
		RequestMessage,
		ResponseMessage,
	]

	def on_connect(self):
		ping = Request(text="Hello, World!")
		self.send(ping)
	
	def on_data(self, data):
		log.debug('Data received: %r' % data)

	def on_end(self):
		pass
