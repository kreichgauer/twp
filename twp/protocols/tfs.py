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


class TFS(twp.protocols.rpc.RPC):
    def __init__(self):
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
                ), StatResult()),
            twp.protocols.rpc.RPCMethod("mkdir", (
                    Path(name="directory"),
                ), twp.values.NoValue()),
            twp.protocols.rpc.RPCMethod("rmdir", (
                    Path(name="directory"),
                ), twp.values.NoValue()),
            twp.protocols.rpc.RPCMethod("remove", (
                    Path(name="directory"),
                    twp.values.String(name="file")
                ), twp.values.NoValue()),
            twp.protocols.rpc.RPCMethod("monitor", (
                    Path(name="directory"),
                    twp.values.Int(name="recursive"),
                    twp.values.Binary(name="host"),
                    twp.values.Int(name="port"),
                ), twp.values.Int()),
            twp.protocols.rpc.RPCMethod("stop_monitoring", (
                    twp.values.Int(name="h"),
                ), twp.values.Int()),
        ]
        super(TFS, self).__init__()

class TFSClient(twp.protocols.rpc.RPCClient):
    protocol_class = TFS

def pack_ip(ip):
    import socket
    ip = socket.inet_pton(socket.AF_INET, ip)
    return ip

def pack_ip6(ip):
    import socket
    return socket.inet_pton(socket.AF_INET6, ip)