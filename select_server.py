import select
import socket
import sys

###

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.settimeout(0.0)

s.bind(('localhost',5285))
s.listen(5)


####

connections = []

while True:
	
	r,w,e = select.select([s]+connections,[],[],5)
	
	print 'writable=%i'%len(w)
	
	for _r in r:
		
		
		if _r is s:
			conn,addr =_r.accept()
			print addr
			print 'accepted connection'	
			conn.settimeout(0.0)
			connections.append(conn)
			
		else:
			
			msg = _r.recv(len('Hello, World!\n'))
			
			if msg:
				
				print msg[:-1]
				sys.stdout.flush()
				
			else:
				
				_r.close()
				connections.remove(_r)
				print len(connections)
				continue
			
		
	print 'loop'
	sys.stdout.flush()
