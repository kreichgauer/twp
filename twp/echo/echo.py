from .. import protocol

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
