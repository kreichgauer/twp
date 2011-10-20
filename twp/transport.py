import select
import socket
import threading
from .protocol import BaseProtocol
from . import log

SELECT_TIMEOUT = 1
SOCKET_BUFSIZE = 1024

class Transport(threading.Thread):
	"""A TWP3 session."""

	protocol_class = BaseProtocol

	def __init__(self, host, port, force_ip_v6=False):
		super(Transport, self).__init__()
		self._lock = threading.Lock()
		self._stop_event = threading.Event()
		self._send_buffer = b''
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
		with self._lock:
			self._send_buffer += msg # TODO encoding?
			log.debug('Queued message: %r' % msg)
	
	def start(self):
		"""Start the send/recv cycle."""
		# Consider auto-starting
		super(Transport, self).start()
		self.protocol.on_connect()

	def stop(self):
		"""Tell the thread to stop its send/recv cycle. Ultimately close the 
		socket and stop the thread."""
		self._stop_event.set()

	def _should_stop(self):
		return self._stop_event.is_set()

	def run(self):
		# TODO Use a thread pool instead of one thread per Transport
		try:
			while not self._should_stop():
				rlist = xlist = [self._socket]
				wlist = rlist if len(self._send_buffer) else []
				# TODO pass timeout and implement shutdown
				rlist, wlist, xlist = select.select(rlist, wlist, xlist, 
					SELECT_TIMEOUT)
				for socket in rlist:
					data = self._socket.recv(SOCKET_BUFSIZE)
					log.debug("Recv'd data over socket: %r" % data)
					self.protocol.on_data(data)
				for socket in wlist:
					with self._lock:
						self._socket.sendall(self._send_buffer)
						log.debug("Sent data over socket: %r" % self._send_buffer)
						self._send_buffer = b''
				for socket in xlist:
					log.warn('exception state on socket')
		finally:
			self._socket.close()
