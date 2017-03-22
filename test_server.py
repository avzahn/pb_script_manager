import socket
import threading
import signal
import sys

### handle SIGTERM

kill = threading.Event()

def exit_server(signo,frame):
	
	global s
	
	print 'exiting...'
	sys.stdout.flush()
	
	kill.set()
	accept_worker.join()
	
	print  'threads joined'
	sys.stdout.flush()
	
	s.close()	
	
	print 'socket closed'
	sys.stdout.flush()
	
	sys.exit()


signal.signal(signal.SIGTERM,exit_server)

### handle new connections

connections = []
addresses = []

def accept_connections(s,c,a):
	
	global new
		
	print 'listener on'
	sys.stdout.flush()
	
	while not kill.is_set():
		
		try:
			#print '(%ii) waiting for new connection...'%(ii,)
			print 'waiting for new connection...'
			#ii += 1
			sys.stdout.flush()
			_c,_a = s.accept()
			c.append(_c)
			a.append(_a)
			new.set()
			
		except:
			print 'no new connection'
			sys.stdout.flush()


ii = 0

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.settimeout(2.5)

s.bind(('localhost',5285))
s.listen(2)

accept_worker = threading.Thread(target=accept_connections,
									args=(s,connections,addresses))
									
accept_worker.start()

new = threading.Event()

try:

	while new.wait():
	
		print addresses[-1]
		sys.stdout.flush()
	
		new.clear()

except:
	print 'main loop exception'
	sys.stdout.flush()
	exit_server(None,None)
	

