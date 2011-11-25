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
number = Integer()
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
		messagedef = "message" & identifier & eq & Or(Regexp(r"[0-7]") > "id", idPair > "extensionId") & lbr & field[:] & rbr > MessageDef

		typedef = Or(structdef, sequencedef, uniondef, forwarddef) > TypeDef
		protocolelement = typedef | messagedef

		protocol =  Drop("protocol") & identifier & eq & ~id & (number > "id") & lbr & protocolelement[:] & rbr > Protocol
		specification = Or(protocol, messagedef, structdef)[:]
