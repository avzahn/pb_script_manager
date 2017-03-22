import signal
import time

def handler(signo,frame):
	pass
	
signal.signal(signal.SIGHUP,handler)


while True:
	
	with open('log', 'a') as f:
		
		print>>f, 'nohup loop'
		time.sleep(2)
