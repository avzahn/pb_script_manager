import subprocess
import threading
import datetime


def external_call(cmds, timeout=1, parent=None):
    """
    Make a series of blocking external calls that time out safely.
    
    @cmds:
        list of lists containing the external calls, each just as would be
        passed to the subprocess module.
        
    @timeout:
        timeout length per entry in cmds
    
    Parent is optionally any object with list fields named stdout and stderr,
    and is only used by external_call_async
    """
    PIPE = subprocess.PIPE
    out,err = [],[]
    
    for cmd in cmds:
    
        proc = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
    
        # python has closure support
        def _call():
        
            _out,_err = proc.communicate() 
            out.append(_out)
            err.append(_err)
        
            if parent != None:
                parent.stdout.append(_out)
                parent.stderr.append(_err)
    
        worker = threading.Thread(target=_call)

        worker.start()
        worker.join(timeout)
    
    if worker.is_alive():
        proc.terminate()
        worker.join()
    
    return out,err

class external_call_async(object):
	"""
	Make a set of nonblocking external calls inside a worker thread that will
    safely time out if the external programs don't terminate.
	
	stdout and stderr end up in the stdout and stderr members.
	
	Usage:
	
		ping = external_call_async([['ping', 'equatorialbear.ucsd.edu']])
	
		if ping.worker.is_alive():
			sleep(1) # or something else while we wait
			
		if ping.stderr[0]:
			do_error_handling()
		
		ret = ping.stdout[0]
	
	
	The current implementation involves launching a new thread within a	new
    thread, so definitely try to batch call external programs within a single
    external_call_async.
	"""
    
    def __init__(self,cmds,timeout=1):
        """
        See external call. cmds and timeout are the exact same thing.
        """
        
        self.stdout = None
        self.stderr = None
        
        self.worker = threading.Thread(target=external_call,
			args=(cmds,timeout,self))
        self.worker.start()
        
def datetime_to_list(dt):
    """
    Helper function to turn a datetime object into a list of integers that can
    be passed to another datetime's __init__
    """
    if dt == None:
        return None
        
    out =  [dt.year, 
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.microsecond]

    return out
    
def datetime_from_list(l):
    
    if l == None:
        return None
        
    return datetime.datetime(*l)
