import os.path
import sys
import logging
import twp
from twp.protocols import tfs

twp.log.setLevel(logging.WARN)

def du_directory(obj, directory):
    reply = obj.listdir(directory=directory)
    dirs = reply.values['result']['directories']
    files = reply.values['result']['files']
    for subdir in dirs:
        dir = []
        dir.extend(directory)
        dir.append(subdir)
        du_directory(obj, dir)
    for file in files:
        reply = obj.stat(directory=directory, file=file)
        stat = reply.values['result']
        path = os.path.join(*directory)
        path = os.path.join(path, file)
        print("%d\t%s" % (stat['size'], path))

def du(host, port, directory):
    client = tfs.TFSClient(host, port)
    adapter = client.get_adapter()
    directory = directory.split("/")
    du_directory(adapter, directory)

def usage():
    print("Usage: %s <host> <port> <directory>" % sys.argv[0])

if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage()
        exit(1)
    du(sys.argv[1], int(sys.argv[2]), sys.argv[3])
