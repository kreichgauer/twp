import sys
import re
from twp import log, protocol, fields, error
from twp.message import Message

class Request(Message):
	id = 0
	text = fields.String()


class Response(Message):
	id = 1
	text = fields.String()
	number_of_letters = fields.Int()

class EchoProtocol(protocol.Protocol):
	protocol_id = 2
	message_types = [
		Request,
		Response,
	]

class EchoClient(protocol.TWPClient):
	protocol_class = EchoProtocol

	def echo(self, text="Hello, World!"):
		ping = Request(text)
		self.send_twp(ping)
		message = self.read_message()
		log.debug(message)


class EchoConsumer(protocol.TWPConsumer):
	protocol_class = EchoProtocol

	def on_message(self, message):
		if isinstance(message, Request):
			log.debug("Request: %s" % message)
			text = message.text
			letters = re.sub('[^A-Za-z]','', text)
			number_of_letters = len(letters)
			response = Response(text, number_of_letters)
			self.send_twp(response)
		else:
			raise error.TWPError("Unexpected Message %s" % message)


class EchoServer(protocol.TWPServer):
    handler_class = EchoConsumer


if __name__ == "__main__":
	client = EchoClient()
	text = sys.argv[1]
	client.echo(text)
