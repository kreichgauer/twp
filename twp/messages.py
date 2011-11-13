from . import values

class Message(types.Complex):
	@property
	def identifier(self):
		"""Set to the Message's identifier, which must be in range(0,7)."""
		raise ValueError("Message without identifier.")

	@property
	def tag(self):
		"""The Message's tag. This equals 4 plus the identifier. Raises a 
		ValueError if the identifier is larger than 7."""
		if self.identifier > 7:
			raise ValueError("Message identifier cannot be greater than 7.")
		return 4 + self.identifier


class MessageError(Message):
	# ID 8 is tag 12, but tag 12 is Registered Extension? Strange...
	identifier = 8
	# Don't raise because tag is greater than 7
	tag = 4 + identifier
	failed_msg_typs = types.Int() # TODO The purpose of this field is unclear...
	error_text = types.String()

