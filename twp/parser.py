from lepl import *

class Protocol(Node): pass
class MessageDef(Node): pass
class StructDef(Node): pass

class ProtocolElement(Node): pass
class TypeDef(ProtocolElement): pass
class MessageDef(ProtocolElement): pass

class StructDef(TypeDef): pass
class SequenceDef(TypeDef): pass
class UnionDef(TypeDef): pass
class ForwardDef(TypeDef): pass

class Field(Node): pass

letter = Letter() | Literal("_")
identifier = Word(letter, letter | Digit()) > "identifier"
number = Integer() >> int
colon = Drop(":")
semicolon = Drop(";")
lt = Drop("<")
gt = Drop(">")
lbr = Drop("{")
rbr = Drop("}")
eq = Drop("=")
id = Literal("ID")

primitiveType = Or("int", "string", "binary", "any")

with TraceVariables():
	with Separator(~Whitespace()[1:]):
		anyDefinedBy = Add(Literal("any") & "defined" & "by")
		anyDefinedByType = anyDefinedBy & identifier

	with Separator(~Whitespace()[:]):
		type = Or(primitiveType, identifier, anyDefinedByType)
		idPair = id & number

		field = Optional("optional") & type & identifier & semicolon > Field
		structdef = "struct" & identifier & Optional(eq & idPair) & lbr & field[1:] & rbr
		sequencedef = "sequence" & lt & type & gt & identifier & semicolon
		casedef = "case" & number & colon & type & identifier & semicolon
		uniondef = "union" & identifier & lbr & casedef[1:] & rbr
		forwarddef = "typedef" & identifier & semicolon
		messageId = Regexp(r"[0-7]") >> int
		messagedef = "message" & identifier & eq & Or(messageId > "id", idPair > "extensionId") & lbr & field[:] & rbr > MessageDef

		typedef = Or(structdef, sequencedef, uniondef, forwarddef) > TypeDef
		protocolelement = typedef | messagedef

		protocol =  Drop("protocol") & identifier & eq & ~id & (number > "id") & lbr & protocolelement[:] & rbr > Protocol
		specification = Or(protocol, messagedef, structdef)[:]


class StubGenerator(object):

	def __init__(self, ast):
		self.ast = ast

		self.indent_level = 0 
		self.indent_step = 4
		self.indent_char = " "
		self.protocols = {}

	def out(self, str):
		# Remember to append a '\n' at the end.
		if len(str):
			str = self._indent_str() + str
		print(str)

	def _indent_str(self):
		return self.indent_char * self.indent_level

	def indent(self):
		self.indent_level += self.indent_step
	
	def dedent(self):
		self.indent_level -= self.indent_step
		if self.indent_level < 0:
			self.indent_level = 0
			raise ValueError("Indent level below 0")

	def generate(self):
		self.out("import twp")
		self.out("")
		for node in self.ast:
			self._generate_node(node)
	
	def _generate_node(self, node):
		node_type = node.__class__.__name__.lower()
		func = getattr(self, "generate_" + node_type)
		return func(node)

	def generate_protocol(self, node):
		if hasattr(node, "TypeDef"):
			pass # TODO implement

		if hasattr(node, "MessageDef"):
			for msg in node.MessageDef:
				self._generate_node(msg)

		self.out("class %sClient(twp.protocol.TWPClient):" % node.identifier[0])
		self.indent()
		self.out("protocol_id = %d" % node.id[0])
		self.out("")

	def generate_messagedef(self, node):
		self.out("class %s(twp.values.Message):" % node.identifier[0])
		self.indent()
		self.out("id = %d" % node.id[0])
		if hasattr(node, 'Field'):
			for field in node.Field:
				self.generate_field(field)
		self.dedent()
		self.out("")

	def generate_field(self, node):
		optional = node[0] == "optional"
		optional_str = "optional=True" if optional else ""
		name = node.identifier[-1]
		field = None
		if node[0] == "anydefinedby" or optional and node[1] == "anydefinedby":
			field = 'twp.values.AnyDefinedBy("%s"' % (node.identifier[0])
			if optional:
				field += ", " + optional_str
			field += ")"
		elif len(node.identifier) == 2:
			# FIXME implement lookup
			raise ValueError("typerefs not yet supported")
		else:
			# Primitiive
			type = node[0] if not optional else node[1]
			field = "twp.values.%s(%s)" % (type.capitalize(), optional_str)
		self.out('%s = %s' % (name, field))
