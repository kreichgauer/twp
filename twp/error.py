class TWPError(Exception):
    """An unrecoverable error while processing a message."""
	pass

class EndOfContent(TWPError):
    """Raised when an End-Of-Content tag is read from the stream."""
    pass