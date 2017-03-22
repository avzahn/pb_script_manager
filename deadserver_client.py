import socket
import sys
import select


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost',5285))



r,w,e = select.select([s],[],[])

msg = r[0].recv(64)

if not msg:
	print 'server connection dropped'
