import sys
from twp import log, protocol, fields
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

	def echo(self, text):
		ping = Request(text="Hello, World!")
		self.send_twp(ping)
		messages = self.recv_messages()
		log.debug(messages)


class EchoConsumer(protocol.TWPConsumer):
	protocol_class = EchoProtocol

	def on_message(self, message):
		text = message.text
		number_of_letters = len(text.replace(" ", ""))
		response = Response(text, number_of_letters)
		self.send_twp(response)


class EchoServer(protocol.TWPServer):
    handler_class = EchoConsumer


if __name__ == "__main__":
	client = EchoClient()
	text = sys.argv[1]
	client.echo(text)
