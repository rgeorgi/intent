"""
Created on Feb 12, 2015

@author: rgeorgi
"""

# -------------------------------------------
# 1) Set up logging
# -------------------------------------------
import logging, sys, os, re, pickle
from shutil import which
from subprocess import PIPE, Popen
from distutils.version import StrictVersion

ENV_LOG = logging.getLogger(__name__)
logging.addLevelName(1000, "NORMAL")

# -------------------------------------------
# 2) Check for standard modules.
# -------------------------------------------

import_errors=False

try:
    import nltk
except ImportError:
    ENV_LOG.critical('NLTK module not installed')
    import_errors = True

try:
    import lxml
except ImportError:
    ENV_LOG.critical('lxml is not installed')
    import_errors = True

try:
    import nose
except ImportError:
    ENV_LOG.critical('nose is not installed')
    import_errors = True

# -------------------------------------------
# Determine the root directory
# -------------------------------------------
from .fileutils import dir_above
from .ConfigFile import ConfigFile
proj_root = dir_above(__file__, 3)

# Path to the main script.
intent_script = os.path.join(os.path.abspath(proj_root), 'intent.py')

# -------------------------------------------
# Load the "env.conf" file
# -------------------------------------------
env_path = os.path.join(proj_root, 'env.conf')
c = None
if not os.path.exists(env_path):
    ENV_LOG.critical('No env.conf file was found. Please create one in the root directory of the project.')
    import_errors = True
else:
    c = ConfigFile(os.path.join(proj_root, 'env.conf'))

# -------------------------------------------
# Try to load XIGT, either by default or in a specified path.
# -------------------------------------------
xigt_dir = None
if c is not None and c.getpath('xigt_dir'):
    xigt_dir = c.getpath('xigt_dir')


# -------------------------------------------
# First, if the xigt directory is specified
# in the config file, try to import that one.
# -------------------------------------------
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

# -------------------------------------------
# Otherwise, try to load the installed module.
# -------------------------------------------
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




# =============================================================================
# Check java version
# =============================================================================
def java_version(path):
    p = Popen([path, '-version'], stderr=PIPE)
    data = p.stderr.read().decode('utf-8')
    version = re.search('java version \"([0-9\.]+)', data, flags=re.I)
    if version:
        version_string = version.group(1)
        return version_string
    else:
        return None

def java_version_correct(v):
    return StrictVersion(v) >= StrictVersion('1.8.0')

java_error = False

java_bin = c.getpath('java_bin') # Is the java binary specified in the config?

# If not, look for it on the path.
if java_bin is None:
    which_java = which('java')
    if which_java is None:
        ENV_LOG.critical('The java_bin is not specified in the config, and does not appear to be on the path.')
        java_error = True
    else:
        v = java_version(which_java)
else:
    if not os.path.exists(java_bin):
        ENV_LOG.critical('The path to the java executable "{}" specified in the config was not found.'.format(java_bin))
        java_error = True
    else:
        v = java_version(java_bin)

# If we haven't yet hit an error, check the version.
if (not java_error) and (not java_version_correct(v)):
    if java_bin is not None:
        ENV_LOG.critical('The path to java is specified in env.conf, but is not version 1.8.0 or higher.')
    else:
        ENV_LOG.critical('The installed java is not version 1.8.0 or higher. Install a newer version, or specify the path with "java_bin" in the config.')
    java_error = True

# =============================================================================
# Exit with notifications.
# =============================================================================

if import_errors:
    ENV_LOG.critical('Necessary python modules were not found. Please install and try again.')
    sys.exit(2)

if java_error:
    sys.exit(2)

from nose.tools import nottest

#===============================================================================
# Now, have the variables conveniently made available. 
#===============================================================================

java_bin         = java_bin
classifier       = c.getpath('classifier_model')
mgiza            = c.getpath('mgiza')
mallet           = c.getpath('mallet')
mallet_bin       = os.path.join(mallet, 'bin/mallet')
xigt_dir         = c.getpath('xigt_dir')
nltk_dir         = c.getpath('nltk_dir')
tagger_dir       = c.getpath('stanford_tagger_dir')
tagger_model     = c.getpath('stanford_tagger_trans')
parser_dir       = c.getpath('stanford_parser_dir')
parser_model     = c.get('stanford_parser_model')
posdict          = c.getpath('pos_dict')
mst_parser       = c.getpath('mst_parser')
fast_align_bin   = c.getpath('fast_align_bin')

# Giza pre-saved data
g_t_dir          = c.getpath('g_t_dir')
g_t_reverse_dir  = c.getpath('g_t_reverse_dir')

# Directories for reproducing experiments:
odin_xigt_dir = c.getpath('odin_xigt_dir')
rg_igt_dir    = c.getpath('rg_igt_dir')
xl_igt_dir    = c.getpath('xl_igt_dir')
hutp_dir      = c.getpath('hutp_dir')
ud2_dir       = c.getpath('ud2_dir')
ctn_xigt      = c.getpath('ctn_xigt')
exp_dir       = c.getpath('exp_dir')
USE_CONDOR    = c.getbool('use_condor', False)
condor_email  = c.get('condor_email')

# =============================================================================
# Load the pickle when requested
# =============================================================================
def load_posdict():
    return pickle.load(open(posdict, 'rb'))

# =============================================================================
# Where the files for testcases are
# =============================================================================
testfile_dir = os.path.join(proj_root, "data/testcases")
xigt_testfiles = os.path.join(testfile_dir, 'xigt')

@nottest
def xigt_testfile(s):
    return os.path.join(xigt_testfiles, s)


#===============================================================================
# Other classpath vars
#===============================================================================
if nltk_dir:
    if not os.path.exists(nltk_dir):
        ENV_LOG.critical('NLTK dir is specified but "{}" not found.'.format(nltk_dir))
        sys.exit(2)
    else:
        sys.path.insert(0, nltk_dir)