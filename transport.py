"""

This file contains all of the interprocess and network communication
code. The primary abstractions here are the uplink and downlink classes,
which provide interprocess communication through reciprocal calls to
push() and pull() methods between connected instances in different
processes.

Communication is by JSON object (that is, the js equivalent of a python
dictionary, as opposed to a JSON list or JSON string). The API
accepts JSON objects as represented by python dictionaries (such as
those returned by the python's stdlib json module) representing
a valid JSON heirarchy. Thus, the only constraint is that the JSON
message being sent is a JSON object at its outer level.

Usage is slightly different than TCP sockets. A server creates a
listener instance, which listens for connections on a list of IP
addresses and ports. listener.select() blocks on a list of link objects
passed to it and the (address, port) pairs it's initialized with,
returning any link(up- or down-) objects that are ready for reading, and
new downlink objects resulting from new connections.

Clients create uplink objects that connect() to a server. Importantly,
an uplink can connect() and push() before the server is ready through 
use of internal buffering and automatic reconnection attempts.



    Example server:
    
        links = [] 
    
        _listener = listener( ['localhost',31415] )
        
        while True:
        
            readable, new_downlinks = _listener.select(links)
            
            for r in readable:
                
                 json_obj = r.pull()  
                 
                 do_stuff(json_obj)
            
            links += new_downlinks
            
    Example client:
    
        msg =  { 'payload': 'Hello, World!' } 

        up = uplink(addr='localhost',port=31415)
        
        up.push(msg)
            
            
Presently, uplink and downlink are implemented as synchronous TCP socket
wrappers. 

"""

import socket
import select
import inspect
import datetime
import json
import errno
from collections import deque

class _DOWNLINK_DEAD(object):
    def __init__(self):
        pass

DOWNLINK_DEAD = _DOWNLINK_DEAD()


class link(object):
    
    def __init__(self):
        
        # reference to containing object
        self.container = None
        
        self.socket = None
        
        # strings are immutable and therefore not the most efficient way
        # to store send and recieve queues, but they are convenient
        self.rq = ''
        self.sq = ''
        
        # circular buffer of (utc datetime object, function name,
        # err message) tuples
        self.errors = deque([],maxlen=512)        
        
    def log(self,msg):
        """
        Record a message, current utc time, and name of the caller in
        self.errors
        """
        
        t = datetime.datetime.utcnow()
        
        # May return None if not CPython
        fname = inspect.currentframe().f_back.f_code.co_name
        
        if fname == None: fname='no stack frame support'
        
        self.errors.append( (t,fname,msg) )
        
        
    def socket_status(self):
        
        try:
            self.socket.getpeername()
            return True
        except socket.error as e:
            self.log(e.args)
            return False
            
    def close(self):
        
        if self.socket_status():
            self.socket.shutdown(socket.SHUT_RDWR)
        
        self.socket.close()
            
        del self.socket
        self.socket = None
        
    def fileno(self):
        return self.socket.fileno()
        
    def push(self,msg):
        """
        Add msg to send buffer and attempt to send() all of it. Returns
        the number of bytes send()'ed or an error object.
        """
        
        self.sq += json.dumps(msg)
        return self.send()  
    
    def pull(self):
        """
        recv() data and return a list of JSON objects subsequently found
        in the recieve buffer. Purges the recieve buffer through the
        last JSON object found
        """
        # update the recieve buffer        
        self.recv()
        
        # look for json objects in the recieve buffer
        
        objs = []
        stack = [None]
    
        cursor = 0
        end = None
    
        for i,c in enumerate(self.rq):
        
            if c == '{' or c == '}':
            
                stack.append(c)
            
                if stack[-2] == '{' and stack[-1] == '}':
                    # matching braces found
                    
                    if len(stack) == 3:
                        # matching braces are outer
                        
                        candidate = self.rq[cursor:i+1]
                        
                        try:
                            objs.append(json.loads(candidate))
                        except:
                            pass
                        
                        end = i+1
                        cursor = i+1
                
                    stack.pop()
                    stack.pop()
        
        # clear the recieve buffer up to the end of the last object
        # just found
        
        if end != None:
            self.rq = self.rq[end:]
            
        return objs
            
    def recv(self):
        """
        Just here as a reminder that subclasses must implement this
        """
        pass
        
    def send(self):
        """
        Just here as a reminder that subclasses must implement this
        """
        pass

class uplink(link):
    """
    Wrap a nonblocking TCP socket intended to connect() to a host.
    Uplinks are uniquely repsonsible for reconnecting and will always
    seek to reestablish a lost connection.
    """
    
    def __init__(self,addr,port,connect_msg=''):
        """
        @connect_msg:
            Message to automatically send() on connect or reconnect
        """
        
        link.__init__(self)
                       
        self.addr=addr
        self.port=port
        
        if isinstance(connect_msg, dict):
            self.connect_msg = json.dumps(connect_msg)
        else:
            self.connect_msg = connect_msg
        
        self.connect()
        
    def connect(self):
        
        if self.socket != None:
            self.close()
        
        self.socket = socket.socket(socket.AF_INET,
                socket.SOCK_STREAM)
        self.socket.settimeout(0.0)
                
        try:
            self.socket.connect( (self.addr,self.port) )
            
            if not self.connect_msg in self.sq:
                self.sq += self.connect_msg
                
        except socket.error as e:
            self.log(e.args)
                   
    def send(self):
        
        if self.socket_status() == False:
            self.connect()
        
        nbytes = None
        
        try:
            nbytes = self.socket.send(self.sq)
            self.sq = self.sq[nbytes:]
        except socket.error as e:
            self.log(e.args)
        
        return nbytes
        
    def recv(self):
        
        nbytes = 0
        
        if self.socket_status() != True:
            self.connect()
            
        while True:
            
            try:
                ret = self.socket.recv(4096)
                self.rq += ret
                nbytes += len(ret)
                
                if ret == '':
                    self.close()
                    break
                    
            except socket.error as e:
                self.log(e.args)
                break
        
        return nbytes
                
    
class downlink(link):
    """
    Wrap a nonblocking TCP socket obtained from socket.accept()
    """
    
    def __init__(self, sock):
        
        link.__init__(self)
        
        self.socket = sock
        self.socket.settimeout(0.0)
        
    def recv(self):
        
        nbytes = 0
        
        while True:
            
            try:
                ret = self.socket.recv(4096)
                self.rq += ret
                nbytes += len(ret)
                
                if ret == '':
                    self.close()
                    break
                
            except socket.error as e:
                self.log(e.args)
                
                if e.errno != errno.EWOULDBLOCK:
                    nbytes = DOWNLINK_DEAD
                
                break
                
        return nbytes
        

    def send(self):
        
        nbytes = None
        
        try:
            nbytes = self.socket.send(self.sq)
            self.sq = self.sq[nbytes:]
        except socket.error as e:
            
            self.log(e.args)
            nbytes = DOWNLINK_DEAD
            
        return nbytes
            

class listener(object):
    """
    Wrap a nonblocking TCP socket intended to bind() and listen()
    """
    
    def __init__(self, locations):
        """
        
        @locations:
            a list of (addr,port) tuples to bind to
        
        """
        
        self.locations = locations
        
        self.bound_sockets = []
        
        for addr__port in locations:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.0)
            sock.bind(addr__port) #bind() expects an (addr,port) tuple
            sock.listen(5)
            self.bound_sockets.append(sock)

    def __del__(self):
        
        for sock in self.bound_sockets:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            


        
    def select(self, wlist ,timeout=3):
        """
        @wlist
            list of downlink or uplink objects to wait on
        """
        
        
        wdict = {}
        for link in wlist:
            wdict[link.fileno()] = link
        
        new_downlinks = []
        readable_links = []
        
        waiting = self.bound_sockets + [link.socket for link in wlist]
        
        readable,w,e = select.select(waiting,[],[],timeout)
        
        for sock in readable:
            
            if sock in self.bound_sockets:
                conn,addr = sock.accept()
                conn.settimeout(0.0)
                new_downlinks.append(downlink(conn))
                
            else:
                readable_links.append(wdict[sock.fileno()])
                
        return readable_links, new_downlinks
      
      

