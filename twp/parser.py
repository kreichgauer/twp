import sys
from lepl import *
from twp import log

class Protocol(Node): pass
class MessageDef(Node): pass
class StructDef(Node): pass

class ProtocolElement(Node): pass
class TypeDef(ProtocolElement): pass
class MessageDef(ProtocolElement): pass

class StructDef(TypeDef): pass
class SequenceDef(TypeDef): pass
class CaseDef(TypeDef): pass
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
		idPair = ~id & number > "extension_id"

		field = Optional("optional") & type & identifier & semicolon > Field
		structdef = Drop("struct") & identifier & Optional(eq & idPair) & lbr & field[1:] & rbr > StructDef
		sequencedef = "sequence" & lt & type & gt & identifier & semicolon > SequenceDef
		casedef = "case" & number & colon & type & identifier & semicolon > CaseDef
		uniondef = "union" & identifier & lbr & casedef[1:] & rbr > UnionDef
		forwarddef = "typedef" & identifier & semicolon > ForwardDef
		messageId = Regexp(r"[0-7]") >> int
		messagedef = "message" & identifier & eq & Or(messageId > "id", idPair) & lbr & field[:] & rbr > MessageDef

		typedef = Or(structdef, sequencedef, uniondef, forwarddef) > TypeDef
		protocolelement = Or(typedef, messagedef) > ProtocolElement

		protocol =  Drop("protocol") & identifier & eq & ~id & (number > "id") & lbr & protocolelement[:] & rbr > Protocol
		specification = Or(protocol, messagedef, structdef)[:] & Eos()


class StubGenerator(object):

	def __init__(self, ast, output_stream=sys.stdout):
		self.ast = ast
		self.output_stream = output_stream

		self.indent_level = 0 
		self.indent_step = 4
		self.indent_char = " "
		self.protocols = {}

	def write(self, str):
		self.output_stream.write(str)

	def writeln(self, str):
		# Remember to append a '\n' at the end.
		if len(str):
			str = self._indent_str() + str
		self.write(str + "\n")

	def start_class(self, name, bases="object"):
		self.writeln("")
		if not isinstance(bases, str):
			bases = ", ".join(bases)
		self.writeln("class %s(%s):" % (name, bases))

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
		self.writeln("import twp")
		for node in self.ast:
			self._generate_node(node)
	
	def _generate_node(self, node):
		node_type = node.__class__.__name__.lower()
		func = getattr(self, "generate_" + node_type)
		return func(node)

	def generate_protocol(self, node):
		# Collect all message names
		message_identifiers = []
		for protocol_element in getattr(node, "ProtocolElement", []):
			if hasattr(protocol_element, "TypeDef"):
				typedef = protocol_element[0]
				self._generate_node(typedef[0])
			else:
				msg = protocol_element[0]
				message_identifiers.append(msg.identifier[0])
				self._generate_node(msg)
		
		self.start_class(node.identifier[0], "twp.protocol.TWPClient")
		self.indent()
		self.writeln("protocol_id = %d" % node.id[0])
		self.writeln("message_types = [")
		self.indent()
		for msg in message_identifiers:
			self.writeln("%s," % msg)
		self.dedent()
		self.writeln("]")
		self.dedent()

	def generate_messagedef(self, node):
		self.start_class(node.identifier[0], "twp.values.Message")
		self.indent()
		if hasattr(node, "id"):
			self.writeln("id = %d" % node.id[0])
		elif hasattr(node, "extension_id"):
			self.writeln("extension_id = %d" % node.id[0])
		for field in getattr(node, "Field", []):
			self.generate_field(field)
		self.dedent()

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
		self.writeln('%s = %s' % (name, field))

	def generate_structdef(self, node):
		self.start_class(node.identifier[0], "twp.values.Struct")
		self.indent()
		if hasattr(node, "extension_id"):
			self.writeln("extension_id = %s" % node.extension_id[0])
		for field in node.Field:
			self.generate_field(field)
		self.dedent()


if __name__ == '__main__':
	if len(sys.argv) == 3:
		output = sys.argv[2]
	elif len(sys.argv) == 2:
		output = sys.stdout
	else:
		print("Usage: twp-parser <input> [<output>]")
		exit(1)
	try:
		input = open(sys.argv[1])
		if isinstance(output, str):
			output = open(output, "w")
		log.debug("Reading input file...")
		idl = input.read()
		log.debug("Parsing input...")
		ast = specification.parse(idl)
		log.debug("Generating stub...")
		gen = StubGenerator(ast, output)
		gen.generate()
	finally:
		input.close()
		if output != sys.stdout:
			output.close()
