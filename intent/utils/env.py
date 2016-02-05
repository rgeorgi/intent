'''
Created on Feb 12, 2015

@author: rgeorgi
'''
import os, sys, logging
from .fileutils import dir_above
from .ConfigFile import ConfigFile
import pickle

# 1) Set up logging ------------------------------------------------------------
ENV_LOG = logging.getLogger(__name__)
logging.addLevelName(1000, "NORMAL")

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

java_bin         = c.getpath('java_bin')
classifier       = c.getpath('classifier_model')
mgiza            = c.getpath('mgiza')
mallet           = c.getpath('mallet')
mallet_bin       = os.path.join(mallet, 'bin/mallet')
xigt_dir         = c.getpath('xigt_dir')
tagger_jar       = c.getpath('stanford_tagger_jar')
tagger_model     = c.getpath('stanford_tagger_trans')
parser_dir       = c.getpath('stanford_parser_dir')
parser_model     = c.get('stanford_parser_model')
posdict          = 0 if not c.getpath('pos_dict') else pickle.load(open(c.getpath('pos_dict'), 'rb'))
odin_data		 = c.getpath('odin_data')
mst_parser       = c.getpath('mst_parser')
fast_align_bin   = c.getpath('fast_align_bin')
fast_align_atool = c.getpath('fast_align_atool')

# =============================================================================
# Where the files for testcases are
# =============================================================================
testfile_dir = os.path.join(proj_root, "data/testcases")
xigt_testfiles = os.path.join(testfile_dir, 'xigt')

def xigt_testfile(s):
    return os.path.join(xigt_testfiles, s)

# =============================================================================
# Set the default environ lang to UTF-8
# =============================================================================
def set_env_lang_utf8():
    env = os.environ
    env['LANG'] = 'en_US.UTF-8'
    return env

#===============================================================================
# Try to import the XIGT module.
#===============================================================================


# First, if there is a version of XIGT specified in the env file, use that

if java_bin is None:
    ENV_LOG.critical('Path to java binary not specified. Please specify in env.conf using java_bin.')
    sys.exit(2)

if not os.path.exists(java_bin):
    ENV_LOG.critical('Path to java_bin "{}" not found.'.format(java_bin))
    sys.exit(2)

# -- 4) If it IS in the env.conf file, but not found, error out.
if xigt_dir:
    if not os.path.exists(xigt_dir):
        ENV_LOG.critical('XIGT dir is specified, but "%s" not found. Unable to import XIGT' % xigt_dir)
        sys.exit(2)

    # -- 5) Try to load it from the env.conf file...
    elif xigt_dir:
        sys.path.insert(0, xigt_dir)
        try:
            import xigt.model
        except ImportError as ie:
            ENV_LOG.critical('Specified XIGT dir "%s" is not valid for the xigt module.' % xigt_dir)
            ENV_LOG.critical(ie)
            sys.exit(2)

else:
    try:
        import xigt.model  # First, try to import the module that's installed.
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

#===============================================================================
# Test other paths...
#===============================================================================

