'''
Created on Aug 31, 2013

@author: rgeorgi
'''
import optparse, sys, os
from ConfigParser import ConfigParser
from utils.commandline import require_opt
from eval.pos_eval import pos_eval
from utils.systematizing import notify
from utils.ConfigFile import ConfigFile
from utils.fileutils import remove_safe

def prop():
	global cp
	c = ConfigParser()
	mydir = os.path.abspath(os.path.dirname(__file__))
	c.read(os.path.join(mydir, 'prototypes.prop'))
	
	root = c.get('prototypes', 'root')
		
	cp = os.path.join(root, 'bin/')
# 	jars = glob(root+'/lib/*jar')
# 	for jar in jars:
# 		cp += ':%s' % jar
	

def extract():
	prop()
	global cp
	cmd = 'java -cp %s edu.berkeley.nlp.prototype.pos.TreebankTextExtractor ' % cp
	cmd += ' -treebankPath /Users/rgeorgi/Documents/Work/treebanks/LDC95T07/'
	cmd += ' -startSection 2'
	cmd += ' -endSection 24'
	cmd += ' -maxNumSentences 8000'
	cmd += ' -outfile /Users/rgeorgi/Dropbox/code/eclipse/prototype-sequence/data/wsj_aria.txt'
# 	cmd += ' -help
	print cmd
# 	os.system(cmd)

if __name__ == '__main__':
# 	p = optparse.OptionParser()
# 	p.add_option('-c', '--conf', help='Configuration file.')
# 	
# 	opts, args = p.parse_args(sys.argv)
# 	
# 	errors = require_opt(opts.conf, 'You must specify a config file with -c or --conf', True)
# 	if errors:
# 		p.print_help()
# 		sys.exit(0)
# 		
# 	c = ConfigFile(opts.conf)
	
	extract()

	notify()