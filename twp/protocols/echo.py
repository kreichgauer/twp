import sys
from twp import log, protocol, values

class Request(values.Message):
	id = 0
	text = values.String()


class Response(values.Message):
	id = 1
	text = values.String()
	number_of_letters = values.Int()


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

if __name__ == "__main__":
	client = EchoClient()
	text = sys.argv[1]
	client.echo(text)
