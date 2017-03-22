import socket
import threading
import signal
import sys
import time

sockets = []

for i in range(5):

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	#s.settimeout(0.0)
	s.connect(('localhost',5285))
	print 'connected'
	
	if  len(sockets) > 0:
		sockets[-1].send('Hello, World!\n')
		#time.sleep(1)
	
	sockets.append(s)


print 'client shutdown'
