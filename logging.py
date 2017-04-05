import datetime

['rsync',
 '-aq',
 '-e',
 'ssh -p 22',
 'alex@cartesianbear.ucsd.edu:/home/alex/parport/',
 '/home/alex/parport/']
now = datetime.datetime.utcnow()


    
class tracked_file(object):
    """
    Represents a file to be rsynced across the network. Because rsync
    uses bandwidth to diff files between computers, it's worth avoiding
    using this class on a large file. Users should consider the higher
    level text_logger class instead, which breaks up large text log
    files automatically.
    """
    def __init__(self, localpath,downpath=None):    
    
        if os.path.isabs(localpath):
            self.localpath = localpath
            
        else:
            self.localpath = os.path.join(os.getcwd(),localpath)
            
        if downpath != None:
            if not os.path.isabs(downpath):
                raise Exception('Downstream path must be absolute')
                
        
    
        # Original if there isn't a downstream for the file
        self.downpath = downpath
    
        # UTC datetime of last time upstream fetched this file
        self.last_upload = None
    
        # UTC datetime of last time this file was written locally
        self.last_write = None
    
        # UTC datetime beyond which local writes are guaranteed to stop
        self.last_active = None
    
        # UTC datetime for when this file's downstream became inactive.
        # If this tracked_file does not have a downstream because it
        # originates locally, this is just self.last_active
        self.decommissioned = None
        
    def print(msg):
        """
        Print to the tracked_file's path. Don't use this unless this
        tracked_file is original (that is, does not have a downstream).
        """
        
        if self.original == False
        
        with open(self.path,'a') as f:
            print>>f,msg
            
        self.last_write = now()
        
    
        
    
    
    
class text_logger(object):
    pass
