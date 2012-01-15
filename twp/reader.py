import struct
import socket
from twp import log
from twp.message import Extension
from twp.error import TWPError, EndOfContent

class TWPReader(object):
    """Reads bytes from a connection and unmarshals them into values."""

    def __init__(self, connection, _recvsize=1024):
        self.connection = connection
        self.buffer = b""
        self.pos = 0
        self._recvsize = _recvsize

    def _advance(self, n):
        assert(n <= self.remaining_byte_length)
        self.pos += n

    def flush(self):
        """Remove processed bytes from the input buffer to start processing a 
        new message."""
        # FIXME better name
        self.buffer = self.buffer[self.pos:]
        self.pos = 0

    @property
    def remaining_byte_length(self):
        return len(self.buffer) - self.pos

    @property
    def processed_bytes(self):
        return self.buffer[:self.pos]

    def _ensure_buffer_length(self, length):
        """Make sure we have at least length unprocessed bytes on the buffer. 
        Read more bytes into the buffer if neccessary."""
        if self.remaining_byte_length < length:
            if not self._read_from_connection():
                raise ReaderError("Connection closed")
        if self.remaining_byte_length < length:
            log.debug("Not enough bytes to unmarshal")
            raise NotEnoughBytes()

    def _read_from_connection(self, size=1024):
        try:
            data = self.connection.recv(self._recvsize)
        except socket.error:
            raise
        if not len(data):
            return False
        log.debug("Recvd %d bytes:\n%s" % (len(data), data))
        self.buffer += data
        return True

    def read_bytes(self, n):
        self._ensure_buffer_length(n)
        end = self.pos + n
        bytes = self.buffer[self.pos:end]
        self._advance(n)
        return bytes

    def read_tag(self):
        return self.read_bytes(1)[0]

    def read_with_format(self, format):
        length = struct.calcsize(format)
        self._ensure_buffer_length(length)
        values = struct.unpack_from(format, self.buffer, self.pos)
        self._advance(length)
        return values[0]

    def read_value(self):
        """Read a TWP value from the stream. Automatically get more bytes from 
        the stream if the buffer does not contain a complete TWP value."""
        tag = self.read_tag()
        log.debug("Read tag %d" % tag)
        if tag == 0:
            raise EndOfContent("Unexpected End-Of-Content")
        elif tag == 1:
            return None
        elif tag == 2:
            # struct
            return self.read_complex()
        elif tag == 3:
            # sequence
            return self.read_complex()
        elif tag in range(4,12): 
            return self.read_union(tag)
        elif tag == 12:
            return self.read_extension(tag)
        elif tag in range(13, 15):
            return self.read_int(tag)
        elif tag in range(15, 17):
            return self.read_binary(tag)
        elif tag in range(17, 128):
            return self.read_string(tag)
        elif tag in range(160, 256):
            return self.read_application_type(tag)
        else:
            # User-defined?
            raise TWPError("Invalid tag: %d" % tag)

    def read_complex(self):
        """Read a complex value from the stream until running into EOC."""
        values = []
        while True:
            try:
                val = self.read_value()
                values.append(val)
            except EndOfContent:
                break
        return values

    def _read_message(self):
        values = []
        extensions = []
        while True:
            try:
                val = self.read_value()
                if isinstance(val, Extension):
                    extensions.append(val)
                else:
                    values.append(val)
            except EndOfContent:
                break
        return values, extensions

    def read_message(self, tag=None):
        """Read a message (or union) from the stream. Returns the id, values and
        extensions."""
        tag = tag or self.read_tag()
        if not 4 <= tag <= 11:
            raise TWPError("Expected message tag but saw %d" % tag)
        id = tag - 4 # or union case
        values, extensions = self._read_message()
        return id, values, extensions

    def read_union(self, tag=None):
        tag = tag or self.read_tag()
        if not 4 <= tag <= 11:
            raise TWPError("Expected union tag but saw %d" % tag)
        case = tag - 4
        return case, self.read_value()

    def read_int(self, tag=None):
        tag = tag or self.read_tag()
        formats = {
            13: "!b",
            14: "!l",
        }
        if not tag in formats:
            raise TWPError("Expected int tag, but saw %d" % tag)
        format = formats[tag]
        return self.read_with_format(format)

    def read_binary(self, tag):
        log.debug("Reading binary")
        formats = {
            15: "!b",
            16: "!I"
        }
        format = formats[tag]
        length = self.read_with_format(format)
        return self.read_bytes(length)

    def read_string(self, tag):
        log.debug("Reading string")
        short_tag = 17
        long_tag = 127
        if tag < long_tag:
            length = tag - short_tag
        else:
            length = self.read_with_format("@I")
        value = self.read_bytes(length)
        try:
            value = value.decode("utf-8")
        except UnicodeError:
            raise TWPError("Failed to utf-8 decode string value")
        return value

    def read_application_type(self, tag):
        return self.connection.protocol.read_application_type(tag)

    def read_extension(self, tag=None):
        start_pos = self.pos
        tag = tag or self.read_tag()
        if tag != 12:
            raise TWPError("Expected extension tag but saw %d" % tag)
        id = self.read_bytes(4)
        id = struct.unpack("!I", id)[0]
        values = self.read_complex()
        end_pos = self.pos
        # Pass the raw bytes so we don't have to marshal this when forwarding
        raw = self.buffer[start_pos:end_pos]
        ext = Extension(id, values, raw=raw)
        return ext


class ReaderError(Exception):
    pass

class NotEnoughBytes(ReaderError):
    pass
