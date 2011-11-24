from lepl import *

letter = Letter() | Literal("_")
identifier = Word(letter, letter | Digit())
number = Integer()
colon = Drop(":")
semicolon = Drop(";")
lt = Drop("<")
gt = Drop(">")
lbr = Drop("{")
rbr = Drop("}")
eq = Drop("=")
id = Literal("ID")

space = Literal("[ \t\r\n]")

primitiveType = Or("int", "string", "binary", "any")

with TraceVariables():
	with Separator(~Whitespace()[1:]):
		anyDefinedBy = Literal("any") & "defined" & "by"

	with Separator(~Whitespace()[:]):
		type = primitiveType | identifier | anyDefinedBy & identifier
		idPair = id & number

		field = Optional("optional") & type & identifier & semicolon
		structdef = "struct" & identifier & Optional(eq & idPair) & lbr & field[1:] & rbr
		sequencedef = "sequence" & lt & type & gt & identifier & semicolon
		casedef = "case" & number & colon & type & identifier & semicolon
		uniondef = "union" & identifier & lbr & casedef[1:] & rbr
		forwarddef = "typedef" & identifier & semicolon
		messagedef = "message" & identifier & eq & (Regexp(r"[0-7]") | idPair) & lbr & field[:] & rbr

		typedef = structdef | sequencedef | uniondef | forwarddef
		protocolelement = typedef | messagedef > List

		protocol =  "protocol" & identifier & eq & ~id & number & lbr & protocolelement[:] & rbr >> 'protocol'
		specification = Or(protocol, messagedef, structdef)[:]
