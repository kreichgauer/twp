import socket
import asyncore
from twp import fields, log, marshalling, reader
from twp.error import TWPError

BUFSIZE = 1024
TWP_MAGIC = b"TWP3\n"

class Protocol(object):
	def init_connection(self, connection):
		# FIXME delete?
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

	def build_message(self, id, values, extensions, raw):
		for cls in self.message_types:
			if cls.id == id:
				msg_type = cls
				break
		if not msg_type:
			raise TWPError("Message not understood: %d" % tag)
		msg = msg_type(*values, extensions=extensions)
		return msg

	def read_application_type(self, tag):
		"""Hook for implementing application types in Protocols."""
		raise NotImplementedError()


class Connection(object):
	reader_class = reader.TWPReader
	def __init__(self):
		self.init_protocol()
		self.init_reader()
		self.buffer = b""

	def init_protocol(self):
		self.protocol = self.protocol_class()
		self.protocol.init_connection(self)

	def init_reader(self):
		"""Initialize an instance of twp.reader.TWPReader to use with this
		session."""
		self.reader = self.reader_class(self)

	def send_twp(self, twp_value):
		"""Send pretty much anything that can be marshalled."""
		log.debug("Sending TWP value %s" % twp_value)
		data = marshalling.marshal(twp_value)
		self.send(data)
		log.debug("Sent data %s" % data)

	def read_message(self):
		id, values, extensions = self.reader.read_message()
		raw = self.reader.processed_bytes
		self.reader.flush()
		message = self.protocol.build_message(id, values, extensions, raw)
		return message


class TWPClient(Connection):
	def __init__(self, host='localhost', port=5000):
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		Connection.__init__(self)
		self.connect(host, port)
		self._init_session()

	def recv(self, *args, **kwargs):
		# Reader wants Connection to quack like a socket
		return self.socket.recv(*args, **kwargs)

	def create_socket(self, family, type):
		sock = socket.socket(family, type)
		sock.setblocking(1)
		self.socket = sock

	def connect(self, host, port):
		self.socket.connect((host, port))

	def _init_session(self):
		protocol_id = marshalling.marshal_int(self.protocol.protocol_id)
		self.send(TWP_MAGIC + protocol_id)

	def send(self, data):
		data = bytes(data)
		self.socket.sendall(data)

	def read_message(self):
		# Blocking socket, just keep trying
		while True:
			try:
				return super(TWPClient, self).read_message()
			except ValueError:
				log.debug("need more bytes")
				pass

	def close(self):
		self.socket.close()


class TWPClientAsync(asyncore.dispatcher_with_send, Connection):
	def __init__(self, host, port, message_handler_func=None, protocol_class=None):
		asyncore.dispatcher_with_send.__init__(self)
		self.protocol_class = protocol_class
		Connection.__init__(self)
		self.message_handler_func = message_handler_func
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		log.debug("Async client connecting to %s %s" % (host, port))
		self.connect( (host, port) )
		protocol_id = marshalling.marshal_int(self.protocol.protocol_id)
		self.out_buffer += TWP_MAGIC
		self.out_buffer += protocol_id

	# TODO TCP needs to know about closes as well...
	def handle_read(self):
		try:
			initial_pos = self.reader.pos
			msg = self.read_message()
			if self.message_handler_func:
				self.message_handler_func(msg, self)
		except ValueError:
			# Rewind
			self.reader.pos = initial_pos

	def send_twp(self, twp_value):
		"""Send pretty much anything that can be marshalled."""
		log.debug("Sending TWP value %s" % twp_value)
		data = marshalling.marshal(twp_value)
		# bug in asyncore? When we .send() while handling another receive, this 
		# client sometimes does not end up in the write queue.
		# Work around: don't send right away, just buffer
		self.out_buffer += data
		log.debug("Sent data %s" % data)


class TWPConsumer(asyncore.dispatcher_with_send, Connection):
	def __init__(self, sock, addr):
		asyncore.dispatcher_with_send.__init__(self, sock)
		Connection.__init__(self)
		self._addr = addr
		log.debug("Connect from %s %s" % self._addr)
		self.has_read_magic = False
		self.has_read_protocol_id = False

	def handle_read(self):
		try:
			initial_pos = self.reader.pos
			if not self.has_read_magic:
				self.read_twp_magic()
			elif not self.has_read_protocol_id:
				self.read_protocol_id()
			else:
				message = self.read_message()
				self.on_message(message)
			if self.reader.remaining_byte_length:
				# We did not process all the bytes, read again
				self.handle_read()
		except ValueError:
			# Rewind
			self.reader.pos = initial_pos
		except reader.ReaderError as e:
			log.warn(e)
			self.close()

	def handle_close(self):
		log.warn("Client disconnected (%s %s)" % self._addr)
		return asyncore.dispatcher_with_send.handle_close(self)

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
	def __init__(self, host, port, handler_class=None):
		asyncore.dispatcher.__init__(self)
		if handler_class:
			self.handler_class = handler_class
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
