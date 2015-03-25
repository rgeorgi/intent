'''
Created on Feb 12, 2015

@author: rgeorgi
'''
import os, sys, logging
from .fileutils import dir_above
from .ConfigFile import ConfigFile

#===============================================================================
# Set up logging.
#===============================================================================
ENV_LOG = logging.getLogger(__name__)

# Start by geting the project root...
proj_root = dir_above(__file__, 3)

c = ConfigFile(os.path.join(proj_root, 'env.conf'))

#===============================================================================
# Try to import the XIGT module.
#===============================================================================
try:
	import xigt.core  # First, try to import the module that's installed.
except ImportError:
	ENV_LOG.warn('XIGT library is not installed, will try to load from env.conf')
	load_fail = True
else:
	load_fail = False

if load_fail:
	# -- 2) If it's not installed, try to find it in env.conf.
	xigt_dir = c.get('xigt_dir')
	
	# -- 3) If it's not in the env.conf file, error out.
	if xigt_dir is None:
		ENV_LOG.critical('XIGT dir not defined. Unable to import XIGT.')
		sys.exit(2)
		
	# -- 4) If it IS in the env.conf file, but not found, error out.
	elif not os.path.exists(xigt_dir):
		ENV_LOG.critical('XIGT dir "%s" not found. Unable to import XIGT' % xigt_dir)
		sys.exit(2)
		
	# -- 5) Try to load it from the env.conf file...
	else:
		sys.path.append(xigt_dir)
		
		try:
			import xigt.core
		except ImportError:
			ENV_LOG.critical('Specified XIGT dir "%s" is not valid for the xigt module.' % xigt_dir)
			sys.exit(2)
