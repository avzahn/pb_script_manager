import os
import json
import datetime
from utils import *
from text import *
from transport import *

now = datetime.datetime.utcnow()

class host_interface(object):
    """
    Object to organize information needed to communicate with and manage another
    process 
    """
    
    def __init__(self, name, addr, port, sshuser, sshport):
        """
        Self explanatory except that name needs to be unique among all
        host_interface objects.
        """
        
        self.name = name
        self.addr = addr
        self.port = port
        self.sshuser = sshuser
        self.sshport = sshport
        
        self.prefix = 'ssh -p %i %s@%s ' % (sshport,sshuser,addr) 
        
    def ping_status(self):
        """
        Call out to the ping utility to test the route to the host interface.
        Return True if route is ok. For the moment, sends small number of test
        packets and only returns True if none of them are lost.
        """
        
        # Four test packets, 100 millisecond timeout
        cmd = ['ping','-c','4','-w','.1',self.addr] 
        
        out,err = external_call([cmd])
        
        if '0% packet loss' in out[0]:
            return True
        return False

class client(object):
    """
    Used by node objects to describe nodes connected downstream of themselves
    """
    
    def __init__(self, name, host, timeout=None, invocation=None):
        """
        
        @name:
            string that identifies this object uniquely among all the client
            objects held by the same node object
            
        @host:
            host_interface object for the machine hosting the client
            
        @timeout:
            seconds to wait for a pulse signal from client before testing to see
            that its PID is still functioning
            
        @invocation:
            if not None, the text of the call to make over ssh to restart the
            client process, or to start it for the first time after a reboot
    
        
        """ 
        
        self.name = name
        self.host = host
        self.timeout = timeout
        self.invocation = invocation
        
        # blobs 
        self.blobs = []
        
        
    
