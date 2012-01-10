import sys
from twp import log, protocol, fields

class Request(fields.Message):
	id = 0
	text = fields.String()


class Response(fields.Message):
	id = 1
	text = fields.String()
	number_of_letters = fields.Int()


class EchoClient(protocol.TWPClient):
	protocol_id = 2
	message_types = [
		Request,
		Response,
	]

	def echo(self, text):
		ping = Request(text="Hello, World!")
		self.send_message(ping)
		messages = self.recv_messages()
		log.debug(messages)


class EchoConsumer(protocol.TWPConsumer):
	def on_message(self, message):
		text = message.text
		number_of_letters = len(text.replace(" ", ""))
		response = Response(text, number_of_letters)
		self.send_message(response)


class EchoServer(TWPServer):
    handler_class = echo.EchoConsumer


if __name__ == "__main__":
	client = EchoClient()
	text = sys.argv[1]
	client.echo(text)
