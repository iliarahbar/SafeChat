import socket
from threading import Thread
from PyQt6.QtCore import QObject
import hashlib

BUFSIZE = 100000
SERVERIP = "127.0.0.1"
SERVERPORT = 1337

class SSession(QObject):
    def __init__(self):
        pass

    def connect(self, ip, port):
        s = socket.socket()

        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.connect((ip, port))

        return s

    def send(self, socket, data):
    	assert (len(data) <= BUFSIZE)
    	
    	socket.send(data)
    	
    def recv(self, socket):
    	return socket.recv(BUFSIZE)
    
    def md5(self, data):
        h = hashlib.md5()

        h.update(data.encode())

        return h.digest()
    
