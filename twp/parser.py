from lepl import *

def build():
	identifier = Letter() & (Letter() | Digit())[:] > str
	number = Token('1') & Digit()[:] 				> int
	
	with Separator(r'\s+'):
		primitiveType = Or("int", "string", "binary", "any")
		type = primitiveType | identifier | (Token("any") & "defined" & "by" & identifier)

		field = Token("optional")[:1] & type & identifier & ";"
		structdef = "struct" & identifier & (Token("=") & "ID" & number)[:1] & \
			"{" & field[1:] & "}"
		sequencedef = Token("sequence") & "<" & type & ">" & identifier & ";"
		uniondef = "union" & identifier
		casedef = "case" & number / ":" / type & identifier / ";"
		forwarddef = "typedef" & identifier / ";"
		typedef = structdef | sequencedef | uniondef | forwarddef

		messagedef = "message" & identifier / "=" /\
			(Token(r"[0-7]") | "ID" & number) /  "{" / field[:] / "}"

		protocolelement = typedef | messagedef
		protocol = "protocol" & identifier / "=" / "ID" & number / "{" / \
			protocolelement[:] / "}"

		specification = protocol | messagedef | structdef
		return specification
