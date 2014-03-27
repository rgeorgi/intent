'''
Created on Oct 22, 2013

@author: rgeorgi
'''

import os, sys
from optparse import OptionParser
from utils.commandline import require_opt
from utils.systematizing import notify
from utils.ConfigFile import ConfigFile
from eval.pos_eval import pos_eval
import time
from nltk.tag.stanford import POSTagger


def jar():
	global stanford_jar, model
	mydir = os.path.abspath(os.path.dirname(__file__))
	c = ConfigFile(os.path.join(mydir, 'stanford_tagger.prop'))
	
	javahome = c['javahome']
	os.environ['JAVAHOME'] = javahome	
	stanford_jar = c['jar']
	model = c['eng_model']
	

def train(train_file, model_path, delimeter = '/'):
	global stanford_jar
	os.system('java -Xmx4096m -cp %s edu.stanford.nlp.tagger.maxent.MaxentTagger -arch generic -model %s -trainFile %s -tagSeparator %s' % (stanford_jar, model_path, train_file, delimeter))

def test(test_file, model_path, out_file, delimeter):
	global stanford_jar
	cmd = 'java -Xmx4096m -cp %s edu.stanford.nlp.tagger.maxent.MaxentTagger -arch generic -model %s -textFile %s -sentenceDelimiter newline -tokenize false -tagSeparator %s -outputFormat slashTags -outputFile %s' % (stanford_jar, model_path, test_file, delimeter, out_file)
	sys.stderr.write(cmd)
	os.system(cmd)
	
def tag(string, model):
	jar()
	global stanford_jar
	pt = POSTagger(model, stanford_jar)
	return pt.tag(string)
	

if __name__ == '__main__':
	jar()
	
	p = OptionParser()
	p.add_option('-c', '--conf', help='configuration file')
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, "You must specify a configuration file with -c or --conf", True)
	if errors:
		p.print_help()
		sys.exit()
		
	c = ConfigFile(opts.conf)
		
	# Now do the testing and training
	train(c['train_file'],
 		  c['model'],
 		  c['delimeter'])
	test(c['test_file'],
 		 c['model'],
 		 c['out_file'],
 		 c['delimeter'])
	time.sleep(1)
	pos_eval(c['gold_file'], c['out_file'], c['delimeter'])
# 	notify()