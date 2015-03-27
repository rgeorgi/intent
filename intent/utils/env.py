'''
Created on Feb 12, 2015

@author: rgeorgi
'''
import os, sys, logging
from .fileutils import dir_above
from .ConfigFile import ConfigFile

# 1) Set up logging ------------------------------------------------------------
ENV_LOG = logging.getLogger(__name__)

# 2) Determine the project root directory --------------------------------------
proj_root = dir_above(__file__, 3)

# 3) Load the "env.conf" file. -------------------------------------------------
env_path = os.path.join(proj_root, 'env.conf')
if not os.path.exists(env_path):
	ENV_LOG.critical('No env.conf file was found. Please create one in the root directory of the project.')
	sys.exit(2)
	
c = ConfigFile(os.path.join(proj_root, 'env.conf'))

#===============================================================================
# Now, have the variables conveniently made available. 
#===============================================================================

classifier       = c.getpath('classifier_model')
mgiza            = c.getpath('mgiza')
mallet           = c.getpath('mallet')
xigt_dir         = c.getpath('xigt_dir')
tagger_jar       = c.getpath('stanford_tagger_jar')
tagger_model     = c.getpath('stanford_tagger_trans')
parser_jar       = c.getpath('stanford_parser_jar')
parser_model_jar = c.getpath('stanford_parser_model_jar')
parser_model     = c.get('stanford_parser_model')
posdict          = c.getpath('pos_dict')

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

#===============================================================================
# Test other paths...
#===============================================================================

