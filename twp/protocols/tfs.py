import twp.values
import twp.protocol
import twp.protocols.rpc

class Path(twp.values.Sequence):
    _fields = [twp.values.String(),]


class Filelist(twp.values.Sequence):
    _fields = [twp.values.String(),]


class ListResult(twp.values.Struct):
    directories = Filelist()
    files = Filelist()


class StatResult(twp.values.Struct):
    size = twp.values.Int()
    mtime = twp.values.Int()
    atime = twp.values.Int()


class TFS(twp.protocols.rpc.RPCClient):
    def __init__(self, *args, **kwargs):
        super(TFS, self).__init__(*args, **kwargs)
        self.open = twp.protocols.rpc.RPCMethod(self, "open", (
                Path(name="directory"),
                twp.values.String(name="file"),
                twp.values.Int(name="mode"),
            ), twp.values.Int())
        self.read = twp.protocols.rpc.RPCMethod(self, "read", (
                twp.values.Int(name="fh"),
                twp.values.Int(name="count"),
            ), twp.values.Binary())
        self.write = twp.protocols.rpc.RPCMethod(self, "write", (
                twp.values.Int(name="fh"),
                twp.values.Binary(name="data"),
            ), twp.values.NoValue())
        self.seek = twp.protocols.rpc.RPCMethod(self, "seek", (
                twp.values.Int(name="fh"),
                twp.values.Int(name="offset"),
            ), twp.values.NoValue()),
        self.close = twp.protocols.rpc.RPCMethod(self, "close", (
                twp.values.Int(name="filehandle"),
            ), twp.values.NoValue())
        self.listdir = twp.protocols.rpc.RPCMethod(self, "listdir", (
                Path(name="directory"),
            ), ListResult())
        self.stat = twp.protocols.rpc.RPCMethod(self, "stat", (
                Path(name="directory"), 
                twp.values.String(name="file")
            ), ListResult())
        self.mkdir = twp.protocols.rpc.RPCMethod(self, "listdir", (
                Path(name="directory"),
            ), ListResult())
        self.rmdir = twp.protocols.rpc.RPCMethod(self, "listdir", (
                Path(name="directory"),
            ), ListResult())
        self.remove = twp.protocols.rpc.RPCMethod(self, "listdir", (
                Path(name="directory"),
                twp.values.String(name="file")
            ), ListResult())
