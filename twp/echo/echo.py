from .. import log, protocol, types, transport

class Request(types.Message):
	identifier = 0
	text = types.String()


class Response(types.Message):
	identifier = 1
	text = types.String()
	number_of_letters = types.Int()


class Protocol(protocol.BaseProtocol):
	protocol_id = 2
	message_types = [
		Request,
		Response,
	]

	def on_connect(self):
		ping = Request(text="Hello, World!")
		self.send(ping)
	
	def on_data(self, data):
		log.debug('Data received: %r' % data)

	def on_end(self):
		pass


class Transport(transport.Transport):
	protocol_class = Protocol
