'''
Created on Oct 22, 2013

@author: rgeorgi
'''

import os, sys
from ConfigParser import ConfigParser
from optparse import OptionParser
from utils.commandline import require_opt
from utils.systematizing import notify


def jar():
	global stanford_jar
	c = ConfigParser()
	mydir = os.path.abspath(os.path.dirname(__file__))
	c.read(os.path.join(mydir, 'stanford_tagger.prop'))	
	stanford_jar = c.get('stanford', 'jar')
	

def train(train_file, model_path, delimeter = '/'):
	global stanford_jar
	os.system('java -Xmx300m -cp %s edu.stanford.nlp.tagger.maxent.MaxentTagger -arch generic -model %s -trainFile %s -tagSeparator %s' % (stanford_jar, model_path, train_file, delimeter))

def test(test_file, model_path, out_file, delimeter):
	global stanford_jar
	os.system('java -Xmx300m -cp %s edu.stanford.nlp.tagger.maxent.MaxentTagger -arch generic -model %s -testFile %s -tagSeparator %s -outputFile %s' % (stanford_jar, model_path, test_file, delimeter, out_file))
	
	

if __name__ == '__main__':
	jar()
	
	p = OptionParser()
	p.add_option('-c', '--conf', help='configuration file')
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, "You must specify a configuration file with -c or --conf", True)
	if errors:
		p.print_help()
		sys.exit()
		
		
	c = ConfigParser()
	c.read(opts.conf)
	
	# Now do the testing and training
 	train(c.get('tagger', 'train_file'),
 		  c.get('tagger', 'model'),
 		  c.get('tagger', 'delimeter'))
	test(c.get('tagger', 'test_file'),
		 c.get('tagger', 'model'),
		 c.get('tagger', 'out_file'),
		 c.get('tagger', 'delimeter'))
	notify()