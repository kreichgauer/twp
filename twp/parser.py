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

spaces = Space()[1:]

primitiveType = Or("int", "string", "binary", "any")

with TraceVariables():
	with SmartSeparator2(~spaces):
		anyDefinedBy = Literal("any") & "defined" & "by"
		type = primitiveType | identifier | anyDefinedBy & identifier
		idPair = id & number

		field = Optional("optional") & type & identifier
		structdef = "struct" & identifier
		uniondef = "union" & identifier
		casedef = "case" & number
		forwarddef = "typedef" & identifier
		messagedef = "message" & identifier
		
		protocol = "protocol" & identifier

	with DroppedSpace():
		field &= semicolon
		structdef &= Optional(eq & idPair) & lbr & field[1:] & rbr
		sequencedef = "sequence" & lt & type & gt & identifier & semicolon
		uniondef &= lbr & casedef[1:] & rbr
		casedef &= colon & type & ~spaces & identifier & semicolon
		forwarddef &= semicolon
		messagedef &= eq & (Regexp(r"[0-7]") | idPair) & lbr & field[:] & rbr
	
	typedef = structdef | sequencedef | uniondef | forwarddef
	protocolelement = typedef | messagedef

	with DroppedSpace():
		protocol &= eq & idPair & lbr & protocolelement[:] & rbr
		specification = Or(protocol, messagedef, structdef)[:]
