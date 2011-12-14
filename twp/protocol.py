import socket
import asyncore
from twp import log, values
from twp.error import TWPError

BUFSIZE = 1024
TWP_MAGIC = b"TWP3\n"

class Protocol(object):
	def __init__(self):
		self._builder = MessageBuilder(self)

	def init_connection(self, connection):
		self.connection = connection

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

	def define_any_defined_by(self, field, reference_value):
		"""During marshalling/unmarshalling, this can get a field of type
		or `AnyDefinedBy` and the value of its reference field and has to return
		an instance to marshal that field's value into."""
		raise NotImplementedError("No unmarshalling for AnyDefinedBy specified")


class Connection(object):
	def __init__(self):
		self.init_protocol()
		self.buffer = b""

	def init_protocol(self):
		self.protocol = self.protocol_class()
		self.protocol.init_connection(self)

	def send_message(self, msg):
		data = msg.marshal_message(self.protocol)
		self.write(data)

	def recv_messages(self):
		"""Recv messages until all available data can be parsed into messages
		or a timeout occurs. Return the list of parsed messages."""
		# TODO Optional parameter msg_count=1, to guarantee result length?
		# FIXME this needs to be re-written
		messages = []
		while not len(messages):
			try:
				self.read()
			except socket.timeout:
				log.debug("socket timeout")
				break
			messages.extend(self.read_messages())
		return messages

	def read_messages(self):
		messages = []
		while self.buffer:
			# Pass data to message builder.
			message, length = self.protocol._builder.build_message(self.buffer)
			if message:
				self.buffer = self.buffer[length:]
				messages.append(message)
				# Unmarshal more or exit of loop
				continue
			else:
				# Last data chunk was a partial message
				break
		return messages


class TWPClient(Connection):
	def __init__(self, host='localhost', port=5000):
		Connection.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect(host, port)
		self._init_session()

	def create_socket(self, family, type):
		sock = socket.socket(family, type)
		sock.setblocking(1)
		self.socket = sock

	def connect(self, host, port):
		self.socket.connect((host, port))

	def _init_session(self):
		protocol_id = values.Int().marshal(self.protocol.protocol_id)
		self.write(TWP_MAGIC + protocol_id)

	def write(self, data):
		data = bytes(data)
		self.socket.sendall(data)
		log.debug('Sent data: %r' % data)

	def read(self, size=BUFSIZE):
		data = self.socket.recv(size)
		log.debug("Recvd: %s" % data)
		self.buffer += data

	def close(self):
		self.socket.close()


class TWPConsumer(asyncore.dispatcher_with_send, Connection):
	def __init__(self, sock, addr):
		asyncore.dispatcher_with_send.__init__(self, sock)
		Connection.__init__(self)
		self._addr = addr
		log.debug("Connect from %s %s" % self._addr)
		self.buffer = b""
		self.has_read_magic = False
		self.has_read_protocol_id = False

	def handle_read(self):
		print("handle read")
		self.read()
		if not self.has_read_magic:
			self.read_twp_magic()
			return
		if not self.has_read_protocol_id:
			self.read_protocol_id()
			return
		messages = self.read_messages()
		for message in messages:
			self.on_message(message)

	def handle_close(self):
		log.warn("Client disconnected (%s %s)" % self._addr)
		return asyncore.dispatcher_with_send.handle_close(self)

	def write(self, data):
		self.send(data)

	def read(self, size=BUFSIZE):
		data = self.recv(size)
		log.debug("Recvd: %s" % data)
		self.buffer += data

	def read_twp_magic(self):
		magic_length = len(TWP_MAGIC)
		if len(self.buffer) < magic_length:
			return
		magic = self.buffer[:magic_length]
		if magic != TWP_MAGIC:
			log.warn("Wrong TWP magic")
			self.close()
			return
		self.buffer = self.buffer[magic_length:]
		self.has_read_magic = True

	def read_protocol_id(self):
		if len(self.buffer) < 2:
			return
		id = values.Int()
		id, _ = id.unmarshal(self.buffer[:2])
		if id != self.protocol.protocol_id:
			log.warn("Wrong protocol id %s" % id)
			self.close()
			return
		self.buffer = self.buffer[2:]
		self.has_read_protocol_id = True

	def on_message(self, message):
		log.debug("Recvd message: %s" % message)


class TWPServer(asyncore.dispatcher):
	handler_class = None
	def __init__(self, host, port):
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind((host, port))
		self.listen(5)
	
	def handle_accept(self):
		pair = self.accept()
		if not pair is None:
			sock, addr = pair
			handler = self.handler_class(sock, addr)

	def serve_forever(self):
		asyncore.loop()


class MessageBuilder(object):
	def __init__(self, protocol):
		self.protocol = protocol
		self.reset()

	def reset(self):
		"""Called when build_message actually returns a message."""
		# Number of processed bytes
		self.processed = 0
		# Incoming data
		self.data = b""
		# Current message
		self.message = None

	def build_message(self, data):
		"""Feed with bytes. Returns a message or None, and the number of 
		processed bytes."""
		# TODO Reset on TWPError?
		# FIXME This is so broken...
		self.data += data
		if not self.message:
			self._create_message()
		try:
			self._unmarshal_values()
		except ValueError:
			# We need more bytes
			self.reset()
			return None, None
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
		log.info("Trying to unmarshal %r" % self.data)
		values, length = self.message.unmarshal_message(self.data, self.protocol)
		self._did_process(length)

	def _did_process(self, length):
		self.data = self.data[length:]
		self.processed += length
