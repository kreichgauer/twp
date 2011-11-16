from .. import log, protocol, values, transport

class Request(values.Message):
	identifier = 0
	text = values.String()


class Response(values.Message):
	identifier = 1
	text = values.String()
	number_of_letters = values.Int()


class Protocol(protocol.BaseProtocol):
	protocol_id = 2
	message_types = [
		Request,
		Response,
	]

	def on_connect(self):
		ping = Request(text="Hello, World!")
		self.send(ping)
	
	def on_message(self, msg):
		log.debug('Message received: %s' % msg)
		#new_msg = Request(text=msg.text + "...again")
		#self.send(new_msg)

	def on_end(self):
		pass


class Transport(transport.Transport):
	protocol_class = Protocol
