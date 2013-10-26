'''
Created on Aug 31, 2013

@author: rgeorgi
'''
import optparse, sys, os, re
from ConfigParser import ConfigParser
from glob import glob
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
	

def context(rawfile, modelfile):
	prop()
	global cp
# 	conf = '/Users/rgeorgi/Dropbox/code/eclipse/prototype-sequence/conf/orig_test.conf'
	cmd = 'java -server -mx1200m -cp %s edu.berkeley.nlp.prototype.simmodel.WordContextSimilarity ' % cp
	cmd += ' -dataRoot %s' % os.path.dirname(rawfile)
	cmd += ' -prefix %s' % os.path.basename(os.path.splitext(rawfile)[0])
	cmd += ' -outfile %s' % os.path.abspath(modelfile)
	cmd += ' -appendDistance -reduceType RAND_PROJ -contextWindow 2 -directional'

	sys.stderr.write(cmd+'\n')
	os.system(cmd)
	
def train(rawfile, protofile, context_model, sequence_model):
	prop()
	global cp	
	cmd = 'java -server -Xmx2048m -cp %s edu.berkeley.nlp.prototype.PrototypeSequenceModelTrainer ' % cp
	
	cmd += ' -dataRoot %s' % os.path.dirname(rawfile)
	cmd += ' -prefix %s' % os.path.basename(os.path.splitext(rawfile)[0])
	cmd += ' -outfile %s' % os.path.abspath(sequence_model)	
	cmd += ' -protoFile %s' % protofile
	cmd += ' -minIters 0'
	cmd += ' -numIters 10'
	cmd += ' -simModelPath %s' % os.path.abspath(context_model)
	cmd += ' -useSuffixFeatures -useHasHyphen'
	cmd += ' -useInitialCapital'
	cmd += ' -order 1'
# 	cmd += ' -create -execDir %s' % os.path.join(os.path.dirname(context_model), 'exec')

	sys.stderr.write(cmd+'\n')
	os.system(cmd)

def test(rawfile, sequence_model, outfile):
	prop()
	global cp
	cmd = 'java -ea -server -mx1200m -cp %s edu.berkeley.nlp.prototype.PrototypeSequenceModelTester' % (cp)
	cmd += ' -PrototypeSequenceModelTester.modelPath %s' % sequence_model
	cmd += ' -PrototypeSequenceModelTester.outdir %s' % os.path.dirname(outfile)
	cmd += ' -PrototypeSequenceModelTester.inDirRoot %s' % os.path.dirname(rawfile)
	cmd += ' -PrototypeSequenceModelTester.inPrefix %s' % os.path.splitext(os.path.basename(rawfile))[0]
	cmd += ' -PrototypeSequenceModelTester.inExtension .txt'
	cmd += ' -delimeter /'
	cmd += ' -outExtension .tagged'
	os.system(cmd)
	

if __name__ == '__main__':
	p = optparse.OptionParser()
	p.add_option('-c', '--conf', help='Configuration file.')
	
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, 'You must specify a config file with -c or --conf', True)
	if errors:
		p.print_help()
		sys.exit(0)
		
	c = ConfigFile(opts.conf)
	
	remove_safe(c['context_model'])
	remove_safe(c['sequence_model'])
	remove_safe(c['test_file']+'.tagged')

	
	context(c['rawfile'], 
		    c['context_model'])
	train(c['rawfile'],
		  c['protofile'],
		  c['context_model'],
		  c['sequence_model'])
	test(c['test_file'],
		 c['sequence_model'],
		 c['outfile'])
	pos_eval(c['gold_file'],
			 c['test_file']+'.tagged',
			 '/')
	notify()