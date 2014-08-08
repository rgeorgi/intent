'''
Created on Oct 22, 2013

@author: rgeorgi
'''

import os, sys
from optparse import OptionParser
from utils.argutils import require_opt
from utils.systematizing import notify
from utils.ConfigFile import ConfigFile
from eval.pos_eval import pos_eval
import time
import subprocess as sub
from utils.token import tag_tokenizer, tokenize_string

#===============================================================================
# Set up the stanford tagger to run via stdin.
#===============================================================================

def jar():
	global stanford_jar
	mydir = os.path.abspath(os.path.dirname(__file__))
	c = ConfigFile(os.path.join(mydir, 'stanford_tagger.prop'))
	
	javahome = c['javahome']
	os.environ['JAVAHOME'] = javahome	
	stanford_jar = c['jar']
	

class StanfordPOSTagger(object):
	def __init__(self, model):	
		jar()
		self.st = sub.Popen(['java', 
							'-cp', stanford_jar,
							'edu.stanford.nlp.tagger.maxent.MaxentTagger',
							'-model', model, 
							'-tokenize', 'false'],
						
				stdout=sub.PIPE, stdin=sub.PIPE, stderr=sys.stderr)

	def tag_tokenization(self, tokenization, **kwargs):
		return self.tag(tokenization.text(), **kwargs)

	def tag(self, string, **kwargs):
		
		# Lowercase if asked for
		if kwargs.get('lowercase', True):
			string = string.lower()
				
		self.st.stdin.write(bytes(string+'\r\n', encoding='utf-8'))
		self.st.stdin.flush()
		content = self.st.stdout.readline()
		
		# Advance past the newline
		self.st.stdout.readline()
		
		content = content.decode(encoding='utf-8')
		return tokenize_string(content.strip(), tokenizer=tag_tokenizer)
	
	def close(self):
		self.st.kill()
	
#===============================================================================
# Functions to call for testing and training.
#===============================================================================

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
	pt = StanfordPOSTagger(model, stanford_jar)
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