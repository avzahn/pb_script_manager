import socket
import select
import json
import threading
import signal
import shlex
import subprocess
import os.path
import os
import datetime
import socket

from asycnch_json_socket import _socket

class host_machine(object):

    def __init__(self,name, addr, port, sshuser, sshport=22):

        self.name = name
        self.addr = addr
        self.port = port
        self.sshuser = sshuser
        self.sshport = sshport
        
        prefix = 'ssh -p %i %s@%s ' % (sshport,sshuser,addr)    
            
        if addr == 'localhost' or addr == '127.0.0.1':
            prefix = ''
            
        self.prefix = prefix
        
    def test_route_to_host(self):
        
        cmd = ['ping','-c','4','-w','.1',self.addr]

        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
            
        out,err = proc.communicate()
        
        if '0% packet loss' in out:
            return True
        else:
            return False
        
    def dump(self):     
        
        return {
                'obj-type':'host_machine',
                'name':self.name,
                'addr':self.addr,
                'sshuser':self.sshuser,
                'sshport':self.sshport
            }   
        
class tracked_log(object):

    def __init__(self, log_id, originhost, localpath, downhost,
                    downpath, originpath):
        """
        
        @log_id:
            identifier string for this log that must be unique within 
            this server, typically recieved from client
        
        @originhost:
            host_machine object for the computer that originates the log
            
        @downhost:
            host_machine from which to download a copy of the log from
            
        @localpath:
            Absolute path to local copy of log
            
        @downpath:
            Absolute path on downstream host to pull copy of log from
            
        @originpath:
            Absolute path to original copy of log on the originating
            machine
                    
        """
        
        self.log_id = log_id
        self.originhost = originhost
        self.localpath = localpath
        self.originpath = originpath
        self.downpath = downpath
        self.downhost = downhost
        
        # UTC datetime of last upload and download 
        self.last_download = None
        self.last_upload = None
        
        # UTC datetime of client request to unregister or False
        self.unregistered = False
        
        
        sshuser = self.downhost.sshuser
        sshport = self.downhost.sshport
        addr = self.downhost.addr
        
        self.is_local = False
        
        # for now, don't use rsync compression
        self.cmd = ['rsync',
                    '-aq',
                    '-e',
                    '"ssh -p %i"'%sshport,
                    '%s@%s:%s'%(sshuser,addr,downpath),
                    localpath
                    ]
        
        # false if last download ok; utc time of last attempt if error
        self.err = False 
        
        self.worker = None
        self.worker_in_flight = False


    def pull(self):
        """
        Nonblocking rsync call to update internal copy of log.
        
        Obviously calling rsync one file at a time is inefficient, but
        this should do for now. Eventually it could be worth
        implementing a function in the server class that finds a set 
        of groups of files that can be each combined into a single rsync
        command, and then launches rsync in parallel on the whole set.
        """
        
        if self.is_local:
            return
        
        def _pull():
            
            if self.worker_in_flight:
                return
                
            self.worker_in_flight = True
        
            proc = subprocess.Popen(
                    self.cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                    )
                
            out, err = proc.communicate()
            
            if out == None and err == None:
                self.last_download = datetime.datetime.utcnow()
                self.err = False
            else:
                self.err = datetime.datetime.utcnow()
        
            self.worker_in_flight = False
            
        self.worker = threading.Thread(target=_pull)
        self.worker.start()
        

class client(object):
    """
    Represent a node connected from another process, whether local or
    remote.
    """
    
    def __init__(self, name, rootpath, host, invocation=None,
                    sshport=None, sshuser=None):
        """
        @name:
            Unique name for client. Client must respond with this name
            on connection
            
        @rootpath:
            Absolute path to root directory for the server this belongs
            to.
            
        @host:
            host_machine object for machine running the client script
            
        @invocation:
            String containing the shell command needed to start client
            process as seen from the machine where the client is
            running.
            
            If sshport and sshuser are set, __init__ will automatically
            prepend the requisite ssh related part of the command.
            
            Note that if the invocation is too complicated to
            comfortably fit inside a one-liner, the party responsible
            for the client script should package a startup script + 
            config file setup so that the invocation is a simple
            one-liner.
            
            
        A note on logs:
            
            If the client script is local to its upstream, most of the
            time it should register its logs with the server's list of 
            tracked local logs. The server will store those log paths
            belonging to that client script here in self.local_logs..
            
            Remote clients should similarly register any logs they want
            tracked with the uptream's list of mirrored log paths. These
            paths end up in self.remote_logs, and this object will pull 
            them over rsync.
            
            
            
        """
        
        self.name = name
        self.host = host
        
        self.port = None
        self.conn = None
        self.fileno = None
        
        # UTC datetime of last heartbeat signal recieved
        self.pulse = None
                
        # process id on host machine, reported by client
        self.pid = None
                
        self.tracked_logs = {}
        
        
        # directory containing all the logs we've fetched
        self.mirror = os.path.join(rootpath,'mirrors',name)
        if not os.path.exists(self.mirror):
            os.makedirs(self.mirror)

        
    def start(self):
        subprocess.call(self.invocation,shell=True)
        
    def stop(self,force=False):
        flags = ""
        if force: flags = "-9"
        cmd = "%s kill %s %i" % (self.cmd_prefix, flags, self.pid)
        subprocess.call(cmd,shell=True)
        
    def ps_check(self):
        
        cmd = '%s ps -p %i' %(self.cmd_prefix,self.pid)
        
        proc = subprocess.Popen(
                    shlex.split(cmd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                    )
                    
        ret, err = proc.communicate()
        
        return ret

        
    def pull_logs(self):
        """
        Rsync all the self.tracked_logs to self.mirrors. For the
        moment, this is done one log at a time. 

        """
        
        for key in self.tracked_logs:
            
            log = self.tracked_logs[key]
            if log.unregistered == False:
                log.pull()
                
    def add_log(self,log):
        
        if not log_id in self.tracked_logs:
            self.tracked_logs[log.log_id] = log
        
    def set_connected(self, conn):
        
        self.conn = conn
        self.fileno = conn.fileno()
        return self.fileno
        

class server(object):
    """
    
    """
    
    def __init__(self, name, rootdir, upstream,
			locations=None leaf=True):
        """
        
        @name:
            Identifying string for this server. Must be unique on this
            server's upstream.
            
        @rootdir:
            Directory to put all of this server's stuff
            
        @locations:
            List of (address,port) tuples to bind to. If None, defaults
            to [(gethostbyname(gethostname),3141)]
            
        @upstream:
            host_machine object for server upstream of here. Can be
            set to None.
            
        @leaf:
            If True, server has no downstream
            

        """
        if locations == None:
			locations=[socket.gethostbyname(socket.gethostname()),3141]   
			    
		self.locations = locations
        
        self.upstream = upstream

        # clients we expect to see, but aren't necessarily connected,
        # indexed by name
        self.clients = {}
        
        # indexed by socket filenumber
        self.active_clients = {}
        
        # dictionary of functions we may need to call in order to
        # service json messages. By convention, these functions should
        # accept loaded json structures as argument.
        self.dispatch = {}      
        
        # json objects recieved that require attention from all sources 
        self.rbuf = []
        
        if not leaf:
            
            # need sockets to accept() new connections
            self.downstream_sockets = []
            
            for location in locations:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.settimeout(0.0)
				self.downstream_sockets.append(sock)
				

        if upstream != None:
            
            # use a _socket for upstream communication
            self.upstream_socket = _socket(addr=addr, port=port)

    def serve(self):
		
		for i,sock in enumerate(self.downstream_sockets):
			sock.bind( self.locations[i] )
			sock.listen(5)
		
		timeout = 5
		
		waiting = [s for s in self.downstream_sockets]
		
		while True:
		
			readable,w,e = select.select(waiting,[],[],timeout)
			
			for r in readable:

				if r in self.downstream_sockets:
					conn,addr = r.accept()
					conn.settimeout(0.0)
					waiting.append(conn)
					
				else:
					
					# 
					
					
		
		
		
		
		
        

