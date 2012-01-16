import twp.protocol
import twp.protocols.tcp
import operator
from functools import reduce

def faculty(n):
    result = 1
    while n:
        result *= n
        n -= 1
    return result

def runserver():
    ops = [
        (lambda x: reduce(operator.add, x), 9000),
        (lambda x: reduce(operator.mul, x), 9001),
        (lambda x: faculty(x[0]),           9003),
        (lambda x: reduce(operator.sub, x), 9004),
        (lambda x: reduce(operator.div, x), 9005),
    ]
    servers = []
    for func, port in ops:
        server = twp.protocols.tcp.TCPServer('0.0.0.0', port, op_func=func)
        servers.append(server)
    servers[0].serve_forever()

if __name__ == "__main__":
    runserver()
