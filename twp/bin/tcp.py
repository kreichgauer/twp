from twp.protocols import tcp
import twp.message
from twp.utils import pack_ip

for i in range(1):
    print(i)
    ip = pack_ip("127.0.0.1")
    port = 9000
    req=tcp.Request()
    #req.request_id = 0
    #req.arguments = []
    #req.arguments.append((0,42.0))
    #term = [(0,23.0), (0,0.5)]
    #expression = [ip, port, term]
    #req.arguments.append((1,expression))
    c=tcp.TCPClient("localhost", 9000)
    #c.send_twp(req)
    #message = c.read_message()
    #print("Recvd message: %s" % message)

    req.request_id = 1
    req.arguments = [
        (0,42.0),
        (1, [ip, port, [
            (0,23.0),
            (1, [ip, port, [
                (0,5.0),
                (0,666.666)
            ]])
        ]])
    ]
    #ext = tcp.ThreadID(9, 42)
    #req.extensions.append(ext)
    c.send_twp(req)
    message = c.read_message()
    print("Recvd message: %s" % message)
