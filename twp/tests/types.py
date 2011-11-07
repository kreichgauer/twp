import unittest
import struct
from twp import types

class ExampleMessage(types.Message):
	identifier = 1
	fieldA = types.String(optional=True)
	fieldB = types.Int(name="_fieldB")


class MessageTest(unittest.TestCase):
	def testHasAttributes(self):
		m = ExampleMessage()
		self.assertTrue(hasattr(m, "_fields"))
		self.assertTrue(hasattr(m, "fieldA"))
		self.assertIsNone(m.fieldA)
		self.assertIsInstance(m._fields["fieldA"], types.String)
		self.assertEqual(m._fields["fieldA"].name, "fieldA")
		self.assertTrue(hasattr(m, "fieldB"))
		self.assertIsNone(m.fieldB)
		self.assertIsInstance(m._fields["fieldB"], types.Int)
		self.assertEqual(m._fields["fieldB"].name, "_fieldB")

	def testIdentifierAndTag(self):
		baseMessage = types.Message()
		self.assertRaises(ValueError, lambda: baseMessage.identifier)
		message = ExampleMessage()
		self.assertEqual(message.identifier, 1)
		self.assertEqual(message.tag, 5) # 5 + message.identifier

	def testValue(self):
		m = ExampleMessage(fieldA='foobar')
		m.fieldB = 42
		self.assertEqual(m.fieldA, "foobar")
		self.assertEqual(m._fields["fieldA"].value, "foobar")
		self.assertEqual(m.fieldB, 42)
		self.assertEqual(m._fields["fieldB"].value, 42)


class StringTest(unittest.TestCase):
	def testConstants(self):
		string = types.String()
		self.assertEqual(string.SHORT_TAG, 17)
		self.assertEqual(string.LONG_TAG, 127)
		self.assertEqual(string.MAX_SHORT_LENGTH, 109)
		self.assertEqual(string.MAX_LENGTH, 2**32-1)

	def testShortString(self):
		strings = [
			"",
			"a",
			"a" * types.String.MAX_SHORT_LENGTH,
		]
		for value in strings:
			string = types.String(value)
			marshalled = string.marshal()
			tag = types.String.SHORT_TAG + len(value)
			self.assertEqual(marshalled[0], tag)
			decoded = marshalled[1:].decode('utf-8')
			self.assertEqual(value, decoded)

	def testLongString(self):
		strings = [
			"a" * (types.String.MAX_SHORT_LENGTH + 1),
			# "a" * types.String.MAX_LENGTH takes too much time/memory
		]
		for value in strings:
			string = types.String(value)
			marshalled = string.marshal()
			self.assertEqual(marshalled[0], string.LONG_TAG)
			length = struct.pack("!I", len(value))
			self.assertEqual(marshalled[1:5], length)
			decoded = marshalled[5:].decode('utf-8')
			self.assertEqual(len(decoded), len(value))


def runTests():
	unittest.main()

if __name__ == "__main__":
	runTests()
