import threading
import sys

ii = 0

def do_stuff():
	
	global ii
	
	ii += 1

	print ii
	sys.stdout.flush()
	
t = threading.Thread(target=do_stuff,args=())
t.start()
t.join()
