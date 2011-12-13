import sys
import logging
import twp
from twp.protocols import tfs

twp.log.setLevel(logging.WARN)

def du_directory(client, directory):
    reply = client.listdir(directory=directory)
    dirs = reply.values['result']['directories']
    files = reply.values['result']['files']
    for subdir in dirs:
        dir = []
        dir.extend(directory)
        dir.append(subdir)
        du_directory(client, dir)
    for file in files:
        reply = client.stat(directory=directory, file=file)
        stat = reply.values['result']
        path = "/".join(directory) + file
        print("%d\t%s" % (stat['size'], path))
    

def du(host, port, directory):
    client = tfs.TFS(host, port)
    du_directory(client, directory)

def usage():
    print("Usage: %s <host> <port> <directory>" % sys.argv[0])

if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage()
        exit(1)
    du(sys.argv[1], int(sys.argv[2]), sys.argv[3])
