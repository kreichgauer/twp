import threading
from twp import log, values

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
		self._lock = threading.Lock()
		self._data = bytearray()
		self.transport = transport

	def _send(self, data):
		self.transport.send(data)

	def send(self, msg):
		data = msg.marshal()
		self._send(data)

	@property
	def message_tags(self):
		"""Returns a dict mapping ids to subclasses of `Message`."""
		if not hasattr(self, "_message_tags"):
			self._message_tags = dict(
				((msg.tag, msg) for msg in self.message_types)
			)
		return self._message_tags

	@property
	def message_types(self):
		"""Implement to return a list of supported types for the protocol."""
		raise NotImplementedError

	def _marshal_protocol_id(self):
		return values.Int(value=self.protocol_id).marshal()

	def _on_connect(self):
		log.debug("Connected")
		self._send(TWP_MAGIC)
		self._send(self._marshal_protocol_id())
		self.on_connect()

	def on_connect(self):
		"""Implement to handle the connection event."""
		raise NotImplementedError
	
	def on_data(self, data):
		# Append messages to a list, so message handling won't happen while the 
		# lock is held.
		msgs = []
		with self._lock:
			for byte in data:
				self._data.append(byte)
				if byte == values.EndOfContent.tag:
					msgs.append(self._unmarshal_data())
					self._data = bytearray()
		for msg in msgs:
			self.on_message(msgs)

	def _unmarshal_data(self):
		tag = self._data[0]
		message_cls = self.message_tags.get(tag)
		if message_cls is None:
			error = values.MessageError(
				failed_msg_typs=tag,
				error_text="unknown message identifier",
			)
			self.send(error)
			return
		message = message_cls.unmarshal(self._data)
	
	def on_message(self, msg):
		"""Implement to handle incoming messages."""
		raise NotImplementedError

	def on_end(self):
		"""Implement to handle connection end."""
		raise NotImplementedError
