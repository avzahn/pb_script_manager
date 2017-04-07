import subprocess
import threading
import datetime

def external_call(cmd, timeout=1, parent=None):
    """
    Make a blocking call to an external program that times out safely.
    
    cmd is a list containing the external call, just as would be passed
    to the subprocess module.
    
    Parent is optionally any object with fields named stdout and stderr,
    and is only used by external_call_async
    """
    PIPE = subprocess.PIPE
    out,err = [None],[None]
    
    proc = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
    
    def _call():
        _out,_err = proc.communicate() 
        out[0] = _out
        err[0] = _err
        
        if parent != None:
            parent.stdout=_out
            parent.stderr=_err
    
    worker = threading.Thread(target=_call)

    worker.start()
    worker.join(timeout)
    
    if worker.is_alive():
        proc.terminate()
        worker.join()
    
    return out[0],err[0]
    

class external_call_async(object):
	"""
	Make a nonblocking call to an external program inside a worker
	thread that will safely time out if the program doesn't terminate.
	
	stdout and stderr end up in the stdout and stderr members.
	
	Usage:
	
		ping = external_call(['ping', 'equatorialbear.ucsd.edu'])
	
		if ping.worker.is_alive():
			sleep(1) # or something else while we wait
			
		if ping.stderr:
			do_stuff()
		
		ret = ping.stdout
	
	
	The current implementation involves launching a new thread within a
	new thread, so hesitate to launch more than ten or so of these calls
	at once before heavier testing.
    
    This thread within thread approach is probably the single most
    likely bottleneck for scaling this system. I can think of two ways
    a better one might work.
    
    One option is to move to python 3, and use the new subprocess
    module's builtin timeout feature. This would still cost us a python
    thread, but saves the nested second python thread.
    
    Another option is to do this inside a c extension. This is both very
    easy to do and completely nondisruptive, except that the codebase
    would no longer be pure python.
	"""
    
    def __init__(self,cmd,timeout=1):
        
        self.stdout = None
        self.stderr = None
        
        self.worker = threading.Thread(target=external_call,
			args=(cmd,timeout,self))
        self.worker.start()
        
def datetime_to_list(dt):
    """
    Helper function to turn a datetime object into a list of integers
    that can be passed to another datetime's __init__
    """
    if dt == None:
        return None
        
    out =  [dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second, dt.microsecond]

    return out
    
def datetime_from_list(l):
    
    if l == None:
        return None
        
    return datetime.datetime(*l)
