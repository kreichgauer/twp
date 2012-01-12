import socket
def pack_ip(ip):
    return socket.inet_pton(socket.AF_INET, ip)

def pack_ip6(ip):
    return socket.inet_pton(socket.AF_INET6, ip)

def unpack_ip(ip):
    return socket.inet_ntop(socket.AF_INET, ip)

def unpack_ip6(ip):
    return socket.inet_ntop(socket.AF_INET, ip)
