import datetime
import json
import re
import os
from utils import *
['rsync',
 '-aq',
 '-e',
 'ssh -p 22',
 'alex@cartesianbear.ucsd.edu:/home/alex/parport/',
 '/home/alex/parport/']

 
now = datetime.datetime.utcnow


    
class tracked_file(object):
    """
    Represents a file to be rsynced across the network. Because rsync uses
    bandwidth to diff files between computers, it's worth avoiding using this
    class on a large file. Users should consider the higher level 
    text_log_splitter class instead, which breaks up large text log files
    automatically.
    
    Files are tracked across process failures and shutdowns by leaving behind a
    file <localpath>.active with information about an active tracked file.
    
    The actual rsync call and interprocess communication are left to entities
    outside of this file.
    """
    def __init__(self, localpath,downpath=None):    
    
        if os.path.isabs(localpath):
            self.localpath = localpath
            
        else:
            self.localpath = os.path.join(os.getcwd(),localpath)
            
        if downpath != None:
            if not os.path.isabs(downpath):
                raise Exception('Downstream path must be absolute')
        
        self.markerpath = localpath+'.active'
        
        if os.path.exists(self.markerpath):
            self.restore_from_marker()
            return
            
        # Original if there isn't a downstream for the file
        self.downpath = downpath
    
        # UTC datetime of last time upstream fetched this file
        self._last_upload = None
    
        # UTC datetime of last time this file was written locally
        self._last_write = None
    
        # UTC datetime for when this file's downstream became inactive. If this
        # tracked_file does not have a downstream because it originates locally,
        # this is just the time beyond which there will be no more local writes.
        self._decommissioned = None
        
        self.save_marker()
        
        
    @property
    def last_upload(self):
        return self._last_upload
        
    @last_upload.setter
    def last_upload(self, val):
        self._last_upload = val
        self.save_marker()
        
    @property
    def last_write(self):
        return self._last_write
        
    @last_write.setter
    def last_write(self,val):
        self._last_write = val
        self.save_marker()
        
    @property
    def decommissioned(self):
        return self._decommissioned
        
    @decommissioned.setter
    def decommissioned(self,val):
        self._decommissioned = val
        self.save_marker()

    def write(self,msg):
        """
        Write to the tracked_file's path. Don't use this unless this
        tracked_file is original (that is, does not have a downstream).
        """
        
        with open(self.localpath,'a') as f:
            f.write(msg)
            f.flush()
            
        self.last_write = now()

    def purge(self):
        """
        Don't call this unless last_upload is after last_write and last_write is
        after decommissioned.
        """
        os.remove(self.markerpath)
        os.remove(self.localpath)


    def save_marker(self):
        
        d = {'localpath': self.localpath,
            'downpath': self.downpath,
            'last_upload': datetime_to_list(self._last_upload),
            'last_write': datetime_to_list(self._last_write),
            'decommissioned': datetime_to_list(self._decommissioned)
            }
        
        self.status_dict = d
        
        if not os.path.exists(self.localpath):
            return
        
        with open(self.markerpath,'w') as f:
            f.write(json.dumps(self.status_dict))
            f.flush()
            
    def getsize(self):
        """
        Return size of file in bytes
        """
        if os.path.exists(self.localpath):
            return os.path.getsize(self.localpath)
        else:
            return 0
            
    def restore_from_marker(self):
        
        with open(self.markerpath,'r') as f:
            vals = f.read()
            
        d = json.loads(vals)
            
        self.localpath = d.get('localpath')
        self.downpath = d.get('downpath')
        self._last_upload = datetime_from_list(d.get('last_upload'))
        self._last_write = datetime_from_list(d.get('last_write'))
        self._decommissioned=datetime_from_list(d.get('decommissioned'))


class text_log_splitter(object):

    def __init__(self, name, logdir, maxsize):
        """
        @name:
            A name string that as a (name,logdir) pair must be unique
            
        @logdir:
            Working directory for all the files we create
        
        @maxsize:
            Maximum individual filesize, in bytes. Floats are cast to int. MB
            is probably a more natural unit for our purposes, but this is
            simpler.
        """

        self.name = name
        self.logdir = logdir
        self.maxsize = int(maxsize)
        self.strftime_fmt = '%d-%m-%y-%H:%M:%S'
        self.tracked_files = []
        self.current = None
        self.active_file_regex = None
        preexisting = self.scan_for_activity()

        for path in preexisting:
            self.tracked_files.append(tracked_file(path))

        self.new_file()

    def new_file(self):

        fname = '%s_%s' % (self.name, now().strftime(self.strftime_fmt))
        fname = os.path.join(self.logdir, fname)

        self.current = tracked_file(fname)

        self.tracked_files.append(self.current)

    def scan_for_activity(self):

        if self.active_file_regex == None:

            day = '(0[1-9]|[12][0-9]|[3][01])'
            month = '(0[1-9]|1[012])'
            year = '([0-9][0-9])'
            hour = '([01][0-9]|2[0-4])'
            minute = '([0-5][0-9])'
            second = '([0-5][0-9])'

            p = '.*%s_%s\-%s\-%s\-%s:%s:%s\.active$' % \
                (self.name,day,month,year,hour,minute,second)

            self.active_file_regex = re.compile(p)

        found = []

        files = os.listdir(os.getcwd())

        for f in files:

            if self.active_file_regex.match(f):
                found.append(f[:-7])

        return found

    def write(self, text):
        
        if self.current.getsize() > self.maxsize:
            self.new_file()
            self.current.write(text)
            return self.current
            
        self.current.write(text)    
        
        return None
        
            
            
        
        
