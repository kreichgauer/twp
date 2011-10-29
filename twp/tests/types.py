import unittest
from twp import types

class ExampleMessage(types.Message):
	fieldA = types.Field(types.String, optional=True)
	fieldB = types.Field(types.Int, name="_fieldB")

class MessageTest(unittest.TestCase):
	def setUp(self):
		pass

	def tearDown(self):
		pass

	def testHasAttributes(self):
		m = ExampleMessage()
		self.assertTrue(hasattr(m, '_fields'))
		self.assertTrue(hasattr(m, 'fieldA'))
		self.assertIsNone(m.fieldA)
		self.assertIsInstance(m._fields['fieldA'], types.Field)
		self.assertTrue(hasattr(m, 'fieldB'))
		self.assertIsNone(m.fieldB)
		self.assertIsInstance(m._fields['fieldB'], types.Field)

if __name__ == '__main__':
	unittest.main()