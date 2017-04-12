import os
import json
import datetime
from utils import *
from text import *
from transport import *

now = datetime.datetime.utcnow()

class host_interface(object):
    
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
        
class leaf(object):
    
    def __init__(self, name, upstream_host, local_host):
        
        
        self.name = name
        self.local = local_host
        self.upstream = upstream_host
        
        self.pid = None
               
        # tracked_logs indexed by path
        self.logs = {}
        
        self.uplink = None
        
        # handler function dispatch table for upstream requests
        self.dispatch = {}
        
        
        def log
        
        
        
        
        
        self.dispatch['']
        
        
        
    def connect(self):
        
        self.pid = os.getpid()
        
        msgdict = {'obj-id': 'connect',
                    'clientname': self.name,
                    'hostname': self.local.name,
                    'pid': self.pid
                    }
        

        
        self.uplink = uplink(self.upstream.addr,
            self.upstream.port,
            connect_msg = msgdict
            )
            
    def check_in(self):
        
        msgdict = {'obj-id': 'pulse',
                    'clientname': self.name,
                    'hostname': self.local.name,
                    'pid': self.pid,
                    'time': str(now())
                    }
                    
        self.uplink.push(msgdict)
        
        objs = self.uplink.pull()
        
        
        
        
        
        
            
    
    
    
    
    
    
    
