'''
Created on Feb 12, 2015

@author: rgeorgi
'''
import os
from utils.fileutils import dir_above
from utils.ConfigFile import ConfigFile

# Start by geting the project root...
proj_root = dir_above(__file__, 3)

c = ConfigFile(os.path.join(proj_root, 'env.conf'))

odin = c['odin_data']