import socket
import sys
import select

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind(('localhost',5285))
s.listen(5)

conn,addr = s.accept()

s.settimeout(0.0)

conn.close()

print 'closed connection to client'
