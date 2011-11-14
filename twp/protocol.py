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
		self.transport = transport
		# Lock for all data structures that handle *incoming* data
		self._lock = threading.Lock()
		# Incoming, unprocessed bytes
		self._data = bytearray()
		# Values, unmarshaled from incoming bytes, waiting to be composed into
		# messages
		self._values = []

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
		with self._lock:
			# TODO how far do we have to lock?
			for byte in data:
				self._data.append(byte)
			# Unmarshal as many bytes from the data as possible, discard all
			# processed bytes
			for message in self._unmarshal_messages()
				self.on_message(message)

	def _unmarshal_messages(self):
		# Unmarshal bytes. When an EndOfContent is found, compose popped values 
		# and yield composed message. First of a sequence must be message-like,
		# i.e. Message or RegisteredExtension
		while len(self._data):
			if len(self._values) == 0:
				value, length = self._unmarshal_message()
			else:
				value, length = self._unmarshal_value()
			self._values.append(value)
			self._data = self._data[length:]
			if isinstance(value, twp.values.EndOfContent):
				message = self._compose_message(self._values)
				self._values = []
				yield message

	def _unmarshal_message(self, data):
		"""Unmarshals a single message-like value from the bytesequence data.
		Returns the value and the number of bytes processed."""
		pass

	def _unmarshal_value(self, data):
		"""Unmarshals a single field-like value from the bytesequence data. 
		Returns the value and the number of bytes processed."""
		pass

	def _compose_message(self, values):
		message = values[0]
		message_values = values[1:]
		# Paranoia sanity checks
		if not (isinstance(message, twp.values.Message) or
				isinstance(message, twp.values.RegisteredExtension)):
			raise TWPError("Message-like value expected")
		if not isinstance(message_values[-1], twp.values.EndOfContent):
			raise TWPError("Last value must be EndOfContent")
		try:
			message = message.compose(message_values)
		except TWPError:
			# Invalid sequence of values for this message type
			raise
		return message
	
	def on_message(self, msg):
		"""Implement to handle incoming messages."""
		raise NotImplementedError

	def on_end(self):
		"""Implement to handle connection end."""
		raise NotImplementedError
