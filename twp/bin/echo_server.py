import sys
from twp.protocols import echo

def runserver(host, port):
    server = echo.EchoServer(host, port)
    server.serve_forever()

def usage():
    print("Usage: %s <host> <port>" % sys.argv[0])

if __name__ == "__main__":
    if len(sys.argv) != 3:
        usage()
        exit(1)
    runserver(sys.argv[1], int(sys.argv[2]))
