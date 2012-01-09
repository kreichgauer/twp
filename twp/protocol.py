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

	def build_message(self, values, raw):
		tag = raw[0]
		msg_type = None
		for cls in self.message_types:
			if cls.tag == tag:
				msg_type = cls
				break
		if not msg_type:
			raise TWPError("Message not understood: %d" % tag)
		msg = msg_type(values)
		return msg

	def define_any_defined_by(self, field, reference_value):
		"""During marshalling/unmarshalling, this can get a field of type
		or `AnyDefinedBy` and the value of its reference field and has to return
		an instance to marshal that field's value into."""
		raise NotImplementedError("No unmarshalling for AnyDefinedBy specified")


class Connection(object):
	def __init__(self):
		self.init_protocol()
		self.init_reader()
		self.buffer = b""

	def init_protocol(self):
		self.protocol = self.protocol_class()
		self.protocol.init_connection(self)

	def init_reader(self):
		self.reader = self.reader_class(self)

	def send_message(self, msg):
		data = msg.marshal_message(self.protocol)
		self.write(data)

	def read_twp_value(self):
		value = self.reader.read_value()
		raw = self.reader.processed_bytes
		log.debug("Parsed %s into %s" % (raw, value))
		self.reader.flush()
		return value, raw


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
		self.has_read_magic = False
		self.has_read_protocol_id = False
		self.read_twp_magic()
		self.read_protocol_id()

	def handle_read(self):
		value, raw = self.read_twp_value()
		message = self.protocol.build_message(value, raw)
		self.on_message(message)

	def handle_close(self):
		log.warn("Client disconnected (%s %s)" % self._addr)
		return asyncore.dispatcher_with_send.handle_close(self)

	def write(self, data):
		self.send(data)

	def read_twp_magic(self):
		magic_length = len(TWP_MAGIC)
		magic = self.reader.read_bytes(magic_length)
		if magic != TWP_MAGIC:
			log.warn("Wrong TWP magic")
			self.close()
			return
		self.reader.flush()
		self.has_read_magic = True

	def read_protocol_id(self):
		id = self.reader.read_int()
		if id != self.protocol.protocol_id:
			log.warn("Wrong protocol id %s" % id)
			self.close()
			return
		self.reader.flush()
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
