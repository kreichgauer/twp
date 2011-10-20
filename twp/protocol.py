from . import log, types

TWP_MAGIC = 'TWP3\n'

class BaseProtocol(object):

	protocol_id = 2

	def __init__(self, transport):
		self.transport = transport

	def _send(self, data):
		self.transport.send(data)

	def send(self, msg):
		data = types.marshal(msg)
		self._send(data)

	def on_connect(self):
		log.debug('Connected')
		self._send(TWP_MAGIC)
		self._send(b'\x0D\x02')
		self._send(b'\x04')
		echo_req = 'ping'
		tag = chr(17 + len(echo_req))
		self._send(b'' + tag  + echo_req)
		self._send(b'\x00')
		#self.send(self.protocol_id)
	
	def on_data(self, data):
		log.debug('Data received: %r' % data)

	def on_end(self):
		pass
