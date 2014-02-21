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
	

def context(rawfile, modelfile, appendDistance = True, contextWindow = 2, directional = True, reduceType = 'RAND_PROJ'):
	prop()
	global cp
# 	conf = '/Users/rgeorgi/Dropbox/code/eclipse/prototype-sequence/conf/orig_test.conf'
	cmd = 'java -server -mx1200m -cp %s edu.berkeley.nlp.prototype.simmodel.WordContextSimilarity ' % cp
	cmd += ' -dataRoot %s' % os.path.dirname(rawfile)
	cmd += ' -prefix %s' % os.path.basename(os.path.splitext(rawfile)[0])
	cmd += ' -outfile %s' % os.path.abspath(modelfile)
	if directional:
		cmd += ' -directional'
	if reduceType:
		cmd += ' -reduceType %s' % reduceType
	if appendDistance:
		cmd += ' -appendDistance'
	if contextWindow:
		cmd += ' -contextWindow %d' % contextWindow 
	

	sys.stderr.write(cmd+'\n')
	os.system(cmd)
	
def train(rawfile, protofile, context_model, sequence_model,  minIters = 10, numIters = 200, order = 2, useSuffixFeatures = True, useHasHyphen = True, useInitialCapital = True, outdir = None):
	prop()
	global cp	
	cmd = 'java -server -Xmx4048m -cp %s edu.berkeley.nlp.prototype.PrototypeSequenceModelTrainer ' % cp
	
	cmd += ' -dataRoot %s' % os.path.dirname(rawfile)
	cmd += ' -prefix %s' % os.path.basename(os.path.splitext(rawfile)[0])
	cmd += ' -outfile %s' % os.path.abspath(sequence_model)	
	cmd += ' -protoFile %s' % protofile
	cmd += ' -minIters %s' % minIters
	cmd += ' -numIters %s' % numIters
	cmd += ' -simModelPath %s' % os.path.abspath(context_model)
	cmd += ' -numSimilarWords 3'
	cmd += ' -simThreshold 0.35'
	

	
	if outdir:
		if not os.path.exists(outdir):
			try:
				os.makedirs(outdir)
			except:
				pass
		cmd += ' -create'
		cmd += ' -execDir %s/exec' % outdir
		cmd += ' -overwriteExecDir'
		
		
			
	
	if useHasHyphen:
		cmd += ' -useHasHyphen'
	if useSuffixFeatures:
		cmd += ' -useSuffixFeatures'
	if useInitialCapital:
		cmd += ' -useInitialCapital'
	
	cmd += ' -useHasDigit'
		
	cmd += ' -order %s' % order
# 	cmd += ' -create -execDir %s' % os.path.join(os.path.dirname(context_model), 'exec')

	sys.stderr.write(cmd+'\n')
	os.system(cmd)

def test(rawfile, sequence_model, outdir):
	prop()
	global cp
	cmd = 'java -ea -server -mx1200m -cp %s edu.berkeley.nlp.prototype.PrototypeSequenceModelTester' % (cp)
	cmd += ' -PrototypeSequenceModelTester.modelPath %s' % sequence_model
	cmd += ' -PrototypeSequenceModelTester.outdir %s' % outdir
	cmd += ' -PrototypeSequenceModelTester.inDirRoot %s' % os.path.dirname(rawfile)
	cmd += ' -PrototypeSequenceModelTester.inPrefix %s' % os.path.splitext(os.path.basename(rawfile))[0]
	cmd += ' -PrototypeSequenceModelTester.inExtension .txt'
	cmd += ' -delimeter /'
	cmd += ' -outExtension .tagged'
	
	sys.stderr.write(cmd+'\n')
	os.system(cmd)
	
def sanity_check(c):
	prop()
	global cp
	assert os.path.exists(cp), cp
	assert os.path.exists(c['rawfile']), c['rawfile']
	assert os.path.exists(c['test_file']), c['test_file']
	assert os.path.exists(c['gold_file'])
	assert os.path.exists(c['protofile'])
	assert os.path.exists(c['outdir']), 'Outdir "%s" not defined or does not exist' % c['outdir']

if __name__ == '__main__':
	p = optparse.OptionParser()
	p.add_option('-c', '--conf', help='Configuration file.')
	
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, 'You must specify a config file with -c or --conf', True)
	if errors:
		p.print_help()
		sys.exit(0)
		
	c = ConfigFile(opts.conf)
	c.set_defaults({'minIters':0, 'numIters':100, 'order':1})
	sanity_check(c)
	
	eval_file = os.path.join(c['outdir'], os.path.basename(c['test_file']))+'.tagged'
	
# 	remove_safe(c['context_model'])
# 	remove_safe(c['sequence_model'])
# 	remove_safe(eval_file)


	
	#===========================================================================
	# Perform the context model training
# 	#===========================================================================
# 	context(c['rawfile'], 
# 		    c['context_model'], appendDistance = c['appendDistance'],
# 		    					contextWindow = c['contextWindow'],
# 		    					directional = c['directional'],
# 		    					reduceType = c['reduceType'])
# 	
# # 	#===========================================================================
# 	#  Perform the sequence model training.
# 	#===========================================================================
# 	train(c['rawfile'],
# 		  c['protofile'],
# 		  c['context_model'],
# 		  c['sequence_model'], numIters = c['numIters'],
# 		 					   minIters = c['minIters'],
# 		 					   order = c['order'],
# 		 					   useSuffixFeatures = c['useSuffixFeatures'],
# 		 					   useHasHyphen = c['useHasHyphen'],
# 		 					   useInitialCapital = c['useInitialCapital'],
# 		 					   outdir = c['outdir'])
	
	#===========================================================================
	# Perform the testing.
	#===========================================================================
# 	test(c['test_file'],
# 		 c['sequence_model'],
# 		 c['outdir'])
# 	
	#===========================================================================
	# Evaluate.
	#===========================================================================
		

	pos_eval(c['gold_file'],
			 eval_file,
			 '/')
	notify()
