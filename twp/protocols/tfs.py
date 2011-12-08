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
    def open(self, directory, file, mode):
        params = {
            "directory": Path(value=directory),
            "file": twp.values.String(value=file),
            "mode": twp.values.Int(value=mode),
        }
        reply = self.request("open", params, True)

    def read(self, filehandle, count): pass
    def write(self, filehandle, data): pass
    def seek(self, filehandle, offset): pass
    
    def close(self, filehandle):
        params = {
            "filehandle": twp.values.Int(value=filehandle)
        }
        self.request("close", params, False)
