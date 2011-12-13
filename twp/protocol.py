import socket
from twp import log, values
from twp.error import TWPError

SOCKET_READSIZE = 1024
TWP_MAGIC = b"TWP3\n"

class TWPClient(object):
	protocol_id = 2

	def __init__(self, host='localhost', port=5000, force_ip_v6=False):
		self._builder = MessageBuilder(self)
		self._init_socket(host, port, force_ip_v6=False)
		self._init_session()

	def _init_socket(self, host, port, force_ip_v6=False):
		socktype = socket.SOCK_STREAM
		af = socket.AF_INET6 if force_ip_v6 else socket.AF_UNSPEC
		addrinfo = socket.getaddrinfo(host, port, af, socktype)
		for af, socktype, proto, canonname, saddr in addrinfo:
			try:
				self.socket = socket.socket(af, socktype, proto)
			except socket.error as e:
				self.socket = None
				continue
			try:
				self.socket.connect(saddr)
			except socket.error as e:
				self.socket.close()
				self.socket = None
				continue
			break
		if self.socket is None:
			raise ValueError("Invalid address")

	def _init_session(self):
		self._send(TWP_MAGIC)
		protocol_id = values.Int().marshal(self.protocol_id)
		self._send(protocol_id)

	def _send(self, data):
		data = bytes(data)
		pos = 0
		while pos < len(data):
			length = self.socket.send(data[pos:])
			if length < 0:
				raise TWPError("Remote side hung up.")
			pos += length
		log.debug('Sent data: %r' % data)

	def send_message(self, msg):
		data = msg.marshal_message(self)
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

	def recv_messages(self):
		"""Recv messages until all available data can be parsed into messages
		or a timeout occurs. Return the list of parsed messages."""
		# TODO Optional parameter msg_count=1, to guarantee result length?
		messages = []
		while True:
			# Recv data
			try:
				data = self.socket.recv(SOCKET_READSIZE)
			except socket.timeout:
				log.debug("socket timeout")
				break
			if not data:
				log.warn("Remote side hung up")
				raise TWPError("Remote side hung up")
			log.debug("Recvd data: %s" % data)
			# Pass data to message builder.
			while len(data):
				message, length = self._builder.build_message(data)
				if message:
					messages.append(message)
				data = data[length:]
			# TODO this looks a bit ugly
			if not message:
				# Last data chunk was a partial message, continue recv'ign
				continue
			else:
				break
		return messages

	def define_any_defined_by(self, field, reference_value):
		"""During marshalling/unmarshalling, this can get a field of type
		or `AnyDefinedBy` and the value of its reference field and has to return
		an instance to marshal that field's value into."""
		raise NotImplementedError("No unmarshalling for AnyDefinedBy specified")


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

	def build_message(self, data):
		"""Feed with bytes. Returns a message or None, and the number of 
		processed bytes."""
		# TODO Reset on TWPError?
		self.data += data
		if not self.message:
			self._create_message()
		self._unmarshal_values()
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

	def _unmarshal_values(self):
		try:
			values, length = self.message.unmarshal_message(self.data, self.protocol)
			self._did_process(length)
		except ValueError:
			# We need more bytes
			pass

	def _did_process(self, length):
		self.data = self.data[length:]
		self.processed += length
