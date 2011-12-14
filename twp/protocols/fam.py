import twp.values
import twp.protocol

class Path(twp.values.Sequence):
    type = twp.values.String()

class Changed(twp.values.Message):
    id = 0
    directory = Path()
    filename = twp.values.String()

class Deleted(twp.values.Message):
    id = 1
    directory = Path()
    filename = twp.values.String()

class Created(twp.values.Message):
    id = 2
    directory = Path()
    filename = twp.values.String()

class StartExecuting(twp.values.Message):
    id = 3
    directory = Path()
    filename = twp.values.String()

class StopExecuting(twp.values.Message):
    id = 4
    directory = Path()
    filename = twp.values.String()

class FAM(twp.protocol.Protocol):
    protocol_id = 4
    message_types = [
        Changed,
        Deleted,
        Created,
        StartExecuting,
        StopExecuting,
    ]

class FAMClient(twp.protocol.TWPClient):
    protocol_class = FAM

class FAMConsumer(twp.protocol.TWPConsumer):
    protocol_class = FAM
    pass

class FAMServer(twp.protocol.TWPServer):
    handler_class = FAMConsumer
