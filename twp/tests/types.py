import unittest
from twp import types

class ExampleMessage(types.Message):
	identifier = 1
	fieldA = types.Field(types.String, optional=True)
	fieldB = types.Field(types.Int, name="_fieldB")

class FieldTest(unittest.TestCase):
	def setUp(self):
		pass

	def tearDown(self):
		pass

	def testType(self):
		type_ = types.String
		field = types.Field(type_)
		self.assertEquals(field.type, type_)

	def testName(self):
		defaultNameField = types.Field(types.String)
		customNameField = types.Field(types.String, name="foo")
		self.assertEquals(defaultNameField.name, None)
		self.assertEquals(customNameField.name, "foo")

	def testOptional(self):
		self.assertEquals(types.Field(types.String).optional, False)
		self.assertEquals(types.Field(types.String, optional=True).optional, True)

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
		self.assertIsInstance(m._fields["fieldA"], types.Field)
		self.assertEquals(m._fields["fieldA"].name, "fieldA")
		self.assertTrue(hasattr(m, "fieldB"))
		self.assertIsNone(m.fieldB)
		self.assertEquals(m._fields["fieldB"].name, "_fieldB")
		self.assertIsInstance(m._fields["fieldB"], types.Field)

	def testIdentifierAndTag(self):
		baseMessage = types.Message()
		self.assertRaises(ValueError, lambda: baseMessage.identifier)
		message = ExampleMessage()
		self.assertEquals(message.identifier, 1)
		self.assertEquals(message.tag, 5) # 5 + message.identifier


def runTests():
	unittest.main()

if __name__ == "__main__":
	runTests()
