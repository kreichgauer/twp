import twp.values
import twp.protocol
import twp.protocols.rpc

class Path(twp.values.Sequence):
    type = twp.values.String()


class Filelist(twp.values.Sequence):
    type = twp.values.String()


class ListResult(twp.values.Struct):
    directories = Filelist()
    files = Filelist()


class StatResult(twp.values.Struct):
    size = twp.values.Int()
    mtime = twp.values.Int()
    atime = twp.values.Int()


class TFS(twp.protocols.rpc.RPCClient):
    def __init__(self, *args, **kwargs):
        self.methods = [
            twp.protocols.rpc.RPCMethod("open", (
                    Path(name="directory"),
                    twp.values.String(name="file"),
                    twp.values.Int(name="mode"),
                ), twp.values.Int()),
            twp.protocols.rpc.RPCMethod("read", (
                    twp.values.Int(name="fh"),
                    twp.values.Int(name="count"),
                ), twp.values.Binary()),
            twp.protocols.rpc.RPCMethod("write", (
                    twp.values.Int(name="fh"),
                    twp.values.Binary(name="data"),
                ), twp.values.NoValue()),
            twp.protocols.rpc.RPCMethod("seek", (
                    twp.values.Int(name="fh"),
                    twp.values.Int(name="offset"),
                ), twp.values.NoValue()),
            twp.protocols.rpc.RPCMethod("close", (
                    twp.values.Int(name="filehandle"),
                ), twp.values.NoValue(), response_expected=False),
            twp.protocols.rpc.RPCMethod("listdir", (
                    Path(name="directory"),
                ), ListResult()),
            twp.protocols.rpc.RPCMethod("stat", (
                    Path(name="directory"), 
                    twp.values.String(name="file")
                ), ListResult()),
            twp.protocols.rpc.RPCMethod("mkdir", (
                    Path(name="directory"),
                ), ListResult()),
            twp.protocols.rpc.RPCMethod("rmdir", (
                    Path(name="directory"),
                ), ListResult()),
            twp.protocols.rpc.RPCMethod("remove", (
                    Path(name="directory"),
                    twp.values.String(name="file")
                ), ListResult()),
        ]
        super(TFS, self).__init__(*args, **kwargs)