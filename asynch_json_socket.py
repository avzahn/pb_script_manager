import socket
import json
from collections import deque
import sys
import errno
import datetime

utcnow = datetime.datetime.utcnow()

class _socket(object):
    """
    Thin wrapper around an ordinary nonblocking TCP socket for recieving
    JSON objects and transparently handling connection dropouts. Not
    intended for use with sockets that will listen() or bind().
    """
    
    def __init__(self,*args, **kwargs):
        """
        We have two use cases for the _socket class:
        
        1.
                
            _s = _socket(addr=some_addr, port=some_port)
            
        Creates a new socket internally. This socket must be intended to
        connect() only. Note that addr and port must be keyword
        arguments.
        
        Responsibility for attempting to reconnect in case of
        communication failure to lies exclusively with _socket objects
        initialized in this way.
            
            
        2.

            _s = _socket( ordinary_tcp_socket.accept() )
            
        Wraps the socket obtained from a call to socket.accept().

            
        """
        
        if len(args) == 0:
        
            # Use case 1
            self.addr = kwargs[addr]
            self.port = kwargs[port]
        
            self.socket = socket.socket(socket.AF_INET,
                socket.SOCK_STREAM)
                
            self.previously_connected = False
            
            self.is_accept_socket = False
                
            
        else:
            # Use case 2
            self.socket = args[0]
            self.addr, self.port = self.socket.getpeername()
            
            self.previously_connected = True
            self.connected = True
            self.is_accept_socket = True


        self.socket.settimeout(0.0)
        self.fileno = self.socket.fileno()
        
        # message queues for sending and recieving
        self.sq = ''
        self.rq = ''
        
        # number of bytes in sq and rq combined
        self.mem_usage = 0
        
        # maximum self.mem_usage to allow
        self.high_water_mark = int(1e5)

        # circular buffer of (utc datetime, error msg) pairs encountered
        self.errors = deque([],maxlen=512)
        
    def connect(self):
        
        # don't want to use this function if we got our socket from
        # a call to accept()
        if self.is_accept_socket: return

        if self.previously_connected == False:
        
            try:
                self.socket.connect((self.addr,self.port))
                self.connected = True
                self.previously_connected = True
                
            except socket.error as e:
                self.errors.append(\
                    (utcnow(), 'connect: errno=%i'%e.errno))            
        else:
            
            self._reconnect()
            

    def _reconnect(self):
    
        self.socket.close() 
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.fileno = self.socket.fileno()
        self.connected = False
        self.previously_connected = False
        self.connect()
                    
    def recv(self):
        
        if self.connected != True:
            self.connect()
        
        if self.mem_usage > self.high_water_mark:
            # in the future, we may not want to quite delete everything
            # in the recieve queue
            self.rq = ''
            self.errors.append((utcnow(), 'recv: high_water'))
        
        json_objects = []
        
        while True:
            try:
                
                ret = self.socket.recv(4096)
                                
                if ret == '':
                    # connection closed gracefully
                    json_objects.append(None)
                    self.connected = False
                    self.socket.close()
                    self.socket = None
                    break
                    
                self.rq += ret
                self.mem_usage = getsizeof(self.rq) + \
                    self.getsizeof(self.sq)
                    
            except socket.error as e:
                

                if e.errno == errno.EWOULDBLOCK:
                    # caught up with the end of stream
                    break
                
                else:
                    # found a connection problem
                    self.connected = False
                    self.errors.append(\
                        (utcnow(), 'recv: errno=%i'%e.errno))
                
        # search for complete JSON objects in self.rq
            
        candidates,last_idx = split_on_object_candidate(self.rq)        
            
        for candidate in candidates:
            try:
                json_objects.append(json.loads(candidate))
            except:
                pass

        if last_idx != None:
            self.rq = self.rq[last_idx:]
            
        return json_objects
        
        
    def send(self,msg):
        
        if self.connected == False:
            self.connect()
            
            
        # using an immutable object like a string as a send queue is
        # memory inefficient, but it is convenient 
        self.sq += msg
        
        self.mem_usage = getsizeof(self.rq) + self.getsizeof(self.sq)
        
        if self.mem_usage > self.high_water_mark:
            # haven't been able to send in a while...

            self.connected = False
            self.connect()
            self.errors.append((utcnow(), 'send: high_water'))
            
            if self.connected == False:
                return 0
                    
        nbytes_sent = 0
                    
        try:
            nbytes_sent = self.socket.send(self.sq)
            
        except socket.error as e:
            self.connected = False
            self.errors.append((utcnow(), 'send: errno=%i'%e.errno))
                
        
        self.sq = self.sq[nbytes_sent:]
                    
                
def split_on_object_candidate(string):
    """
    Split s into a list of toplevel braced substrings. Returns the
    substring list and the index of the last character in the last
    substring. If no substring is found, the returned index value is
    None.
    """
    
    out = []
    stack = [None]
    
    cursor = 0
    end = None
    
    for i,c in enumerate(string):
        
        if c == '{' or c == '}':
            
            stack.append(c)
            
            if stack[-2] == '{' and stack[-1] == '}':
                
                if len(stack) == 3:
                    out.append(string[cursor:i+1])
                    end = i+1
                    cursor = i+1
                
                stack.pop()
                stack.pop()
                
                
        return out,end
            
