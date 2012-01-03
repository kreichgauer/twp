from twp import log
from twp.error import TWPError, EndOfContent

class TWPReader(object):
    """Reads bytes from a connection and unmarshals them into values."""

    def __init__(self, connection, _recvsize=1024):
        self.connection = connection
        self.socket = socket
        self.buffer = b""
        self.pos = 0
        self._recvsize = _recvsize

    def _advance(self, n):
        assert(n <= self.remaining_bytes)
        self.pos += n

    def flush(self):
        """Remove processed bytes from the input buffer to start processing a 
        new message."""
        # FIXME better name
        self.buffer = buffer[self.pos:]
        self.pos = 0

    @property
    def remaining_bytes(self):
        return len(self.buffer) - self.pos

    def _verify_byte_length(self, length):
        if self.remaining_bytes < length:
            raise ValueError("Not enough bytes")

    def _read_from_connection(self, size=1024):
        data = self.connection.recv(self._recvsize)
        log.debug("Recvd %d bytes:\n%s" % (len(data), data))
        self.buffer += data

    def read_bytes(self, n):
        self._verify_byte_length(n)
        end = self.pos + n
        bytes = self.buffer[self.pos:end]
        self._advance(n)
        return bytes

    def read_format(self, format):
        length = struct.calcsize(format)
        self._verify_byte_length(length)
        values = struct.unpack_from(format, self.buffer, self.pos)
        self._advance(length)
        return values[0]

    def read_message(self):
        """Read a message from the stream."""
        # FIXME better name- read_complex?
        values = []
        while True:
            try:
                val = self.read_value()
                values.append(val)
            except EndOfContent:
                break
        return values

    def read_value(self):
        """Read a TWP value from the stream. Automatically get more bytes from 
        the stream if the buffer does not contain a complete TWP value."""
        while True:
            try:
                value = self._read_value()
                break
            except ValueError:
                log.debug("Not enough bytes while unmarshalling from buffer."
                          "Reading from socket and trying again.")
                self._read_from_connection()
        return value

    def _read_value(self):
        tag = self.read_bytes(1)[0]
        log.debug("Read tag %d" % tag)
        if tag == 0:
            raise EndOfContent("Unexpected End-Of-Content")
        elif tag == 1:
            return None
        elif tag == 2:
            # struct
            return self.read_message()
        elif tag == 3:
            # sequence
            return self.read_message()
        elif tag in range(4,12):
            # message / union
            return self.read_message()
        elif tag == 12:
            return self.read_extension()
        elif tag == 13:
            return self.read_int_short()
        elif tag == 14:
            return self.read_int_long()
        elif tag in (15, 17):
            return self.read_binary(tag)
        elif tag in range(17, 128):
            return self.read_string(tag)
        else:
            # User-defined?
            raise TWPError("Invalid tag: %d" % tag)

    def read_int_short(self):
        log.debug("Reading short int")
        return self.read_with_format("@b")
    
    def read_int_long(self):
        log.debug("Reading long int")
        return self.read_with_format("@l")

    def read_binary(self, tag):
        log.debug("Reading binary")
        format = {
            15: "@b",
            16: "@I"
        }
        length = self.read_with_format(format)
        return self.read_bytes(length)

    def read_string(self, tag):
        log.debug("Reading string")
        short_tag = 17
        long_tag = 127
        if tag < long_tag:
            length = tag - short_tag
        else:
            length = self.read_format("@I")
        value = self.read_bytes(length)
        try:
            value = value.decode("utf-8")
        except UnicodeError:
            raise TWPError("Failed to utf-8 decode string value")
        return value

    def read_extension(self, tag):
        raise TWPError("Cannot handle extension %s" % tag)
