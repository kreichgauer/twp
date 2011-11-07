from twp import log, types

TWP_MAGIC = b"TWP3\n"

class Field(object):
	type = None
	name = None
	value = None


class Message(object):
	id = None
	fields = None


class BaseProtocol(object):

	protocol_id = 2

	def __init__(self, transport):
		self.transport = transport

	def _send(self, data):
		self.transport.send(data)

	def send(self, msg):
		self._send(msg.marshal())

	@property
	def messages(self):
		"""Returns a dict mapping ids to subclasses of `Message`."""
		if not hasattr(self, "_messages"):
			self._messages = dict(
				((msg.id, msg) for msg in self.message_types)
			)
		return self._messages

	@property
	def message_types(self):
		"""Returns a list of supported types for the protocol."""
		return types.builtin_types

	def _marshal_protocol_id(self):
		return types.Int(value=self.protocol_id).marshal()

	def _on_connect(self):
		log.debug("Connected")
		self._send(TWP_MAGIC)
		self._send(self._marshal_protocol_id())
		self.on_connect()

	def on_connect(self):
		"""Implement to handle the connection event."""
		raise NotImplementedError
	
	def on_data(self, data):
		"""Implement to handle incoming data."""
		# TODO Implement message parsing here, based on data provided by child class
		raise NotImplementedError

	def on_end(self):
		"""Implement to handle connection end."""
		raise NotImplementedError
