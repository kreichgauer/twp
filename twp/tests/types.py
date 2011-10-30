import unittest
from twp import types

class ExampleMessage(types.Message):
	identifier = 1
	fieldA = types.String(optional=True)
	fieldB = types.Int(name="_fieldB")


class MessageTest(unittest.TestCase):
	def setUp(self):
		pass

	def tearDown(self):
		pass

	def testHasAttributes(self):
		m = ExampleMessage()
		self.assertTrue(hasattr(m, "_fields"))
		self.assertTrue(hasattr(m, "fieldA"))
		self.assertIsNone(m.fieldA)
		self.assertIsInstance(m._fields["fieldA"], types.String)
		self.assertEquals(m._fields["fieldA"].name, "fieldA")
		self.assertTrue(hasattr(m, "fieldB"))
		self.assertIsNone(m.fieldB)
		self.assertIsInstance(m._fields["fieldB"], types.Int)
		self.assertEquals(m._fields["fieldB"].name, "_fieldB")

	def testIdentifierAndTag(self):
		baseMessage = types.Message()
		self.assertRaises(ValueError, lambda: baseMessage.identifier)
		message = ExampleMessage()
		self.assertEquals(message.identifier, 1)
		self.assertEquals(message.tag, 5) # 5 + message.identifier

	def testValue(self):
		m = ExampleMessage(fieldA='foobar')
		m.fieldB = 42
		self.assertEquals(m.fieldA, "foobar")
		self.assertEquals(m._fields["fieldA"].value, "foobar")
		self.assertEquals(m.fieldB, 42)
		self.assertEquals(m._fields["fieldB"].value, 42)


def runTests():
	unittest.main()

if __name__ == "__main__":
	runTests()
