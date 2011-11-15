import select
import socket
import threading
from .protocol import BaseProtocol
from .error import TWPError
from . import log

SOCKET_TIMEOUT = 1.0
SOCKET_READSIZE = 1024

class Transport(threading.Thread):
	"""A TWP3 session."""

	protocol_class = BaseProtocol

	def __init__(self, host, port, force_ip_v6=False):
		super(Transport, self).__init__()
		self._lock = threading.Lock()
		self._stop_event = threading.Event()
		self._init_protocol()
		self._init_socket(host, port, force_ip_v6)

	def _init_protocol(self):
		self.protocol = self.protocol_class(self)

	def _init_socket(self, host, port, force_ip_v6=False):
		socktype = socket.SOCK_STREAM
		af = socket.AF_INET6 if force_ip_v6 else socket.AF_UNSPEC
		addrinfo = socket.getaddrinfo(host, port, af, socktype)
		for af, socktype, proto, canonname, saddr in addrinfo:
			try:
				self._socket = socket.socket(af, socktype, proto)
				self._socket.settimeout(SOCKET_TIMEOUT)
			except socket.error as e:
				self._socket = None
				continue
			try:
				self._socket.connect(saddr)
			except socket.error as e:
				self._socket.close()
				self._socket = None
				continue
			break
		if self._socket is None:
			raise ValueError("Invalid address")

	def send(self, msg):
		"""Queue msg for transmission over the socket."""
		msg = bytes(msg)
		self._socket.sendall(msg) # TODO encoding?
		log.debug('Sent message: %r' % msg)
	
	def start(self):
		"""Start the recv cycle."""
		# Consider auto-starting
		super(Transport, self).start()
		self.protocol._on_connect()

	def stop(self):
		"""Tell the thread to stop its recv cycle. Ultimately close the 
		socket and stop the thread."""
		self._stop_event.set()

	def _should_stop(self):
		return self._stop_event.is_set()

	def run(self):
		try:
			while not self._should_stop():
				data = self._socket.recv(SOCKET_READSIZE)
				if not data:
					log.warn("Remote side hung up")
					break
				self.protocol.on_data(data)
		finally:
			self._socket.close()
