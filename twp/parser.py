from lepl import *

letter = Letter() | Literal("_")
identifier = Word(letter, letter | Digit())
number = Integer()
colon = Literal(":")
semicolon = Literal(";")
lt = Literal("<")
gt = Literal(">")
lbr = Literal("{")
rbr = Literal("}")
eq = Literal("=")
id = Literal("ID")

spaces = ~Space()[1:]

with TraceVariables():
	with SmartSeparator2(spaces):
		primitiveType = Or("int", "string", "binary", "any")
		anyDefinedBy = Literal("any") & "defined" & "by"
		type = primitiveType | identifier | anyDefinedBy & identifier

		# SmartSeparator1/2 leaves out the space between the optional literal
		# and the remaining line here.
		field = Optional(Literal("optional")) & type & identifier / ~semicolon
		structdef = Literal("struct") & identifier & Optional(~eq / ~id & number) &\
			~lbr & field[1:] & ~rbr
		sequencedef = Literal("sequence") & ~lt & type & ~gt & identifier & ~semicolon
		uniondef = Literal("union") & identifier
		casedef = Literal("case") & number / ~colon / type & identifier / ~semicolon
		forwarddef = Literal("typedef") & identifier / ~semicolon
		typedef = structdef | sequencedef | uniondef | forwarddef

		messagedef = Literal("message") & identifier / ~eq /\
			(Regexp(r"[0-7]") | ~id & number) / ~lbr / field[:] / ~rbr

		protocolelement = typedef | messagedef
		protocol = Literal("protocol") & identifier / ~eq / ~id & number / ~lbr /\
			protocolelement[:] / ~rbr

		specification = (protocol | messagedef | structdef)[:]
		#return specification
