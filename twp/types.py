TYPE_TAGS = {
	int: 13
}

def marshal(data):
	# TODO
	assert(type(data) == int and data < 128)
	tag = TYPE_TAGS[type(data)]
	val = bytearray()
	val.append(tag)
	val.append(data)
	return val