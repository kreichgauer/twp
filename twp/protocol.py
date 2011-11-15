import threading
from twp import log, values
from twp.error import TWPError

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
		self._builder = MessageBuilder(self)

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
			log.debug("Recvd data: %s" % data)
			while len(data):
				message, length = self._builder.build_message(data)
				if message:
					self.on_message(message)
				data = data[length:]

	def on_message(self, msg):
		"""Implement to handle incoming messages."""
		raise NotImplementedError

	def on_end(self):
		"""Implement to handle connection end."""
		raise NotImplementedError


class MessageBuilder(object):
	def __init__(self, protocol):
		self.protocol = protocol
		self.reset()

	def reset(self):
		"""Called when build_message actually returns a message."""
		# Incoming data
		self.data = b""
		# Number of processed bytes
		self.processed = 0
		# Current message
		self.message = None
		# Iterator keeping track which field we're at
		self.field_iterator = None
		self.current_field = None

	def build_message(self, data):
		"""Feed with bytes. Returns a message or None, and the number of 
		processed bytes."""
		# TODO Reset on TWPError?
		self.data += data
		if not self.message:
			self._create_message()
		self._unmarshal_values()
		result = None, self.processed
		if self._result_ready():
			result = self.message, self.processed
			self.reset()
		return result

	def _create_message(self):
		tag = self.data[0]
		message = None
		for message_type in self.protocol.message_types:
			if message_type.handles_tag(tag):
				message = message_type()
				break
		if message is None:
			raise TWPError("Unknown message tag %d" % tag)
		self.message = message
		self.field_iterator = iter(self.message._fields.values())
		self._did_process(1)

	def _unmarshal_values(self):
		if self.current_field is None:
			self._next_field()
		while not self.current_field is None:
			try:
				value, length = self.current_field.unmarshal(self.data)
			except ValueError:
				# We need more bytes
				break
			self._did_process(length)
			self._next_field()
			# FIXME handle EndOfContent
			# TODO handle extensions

	def _did_process(self, length):
		self.data = self.data[length:]
		self.processed += length

	def _next_field(self):
		try:
			self.current_field = next(self.field_iterator)
		except StopIteration:
			self.current_field = None

	def _result_ready(self):
		return self.current_field is None
