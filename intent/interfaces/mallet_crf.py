'''
Created on Apr 4, 2014

@author: rgeorgi
'''

# Global imports ---------------------------------------------------------------
import argparse, os, sys, re
import subprocess as sub

# Internal Imports -------------------------------------------------------------
from intent.utils.argutils import existsfile
from intent.utils.ConfigFile import ConfigFile
from intent.eval.pos_eval import simple_tagger_eval

def setup():
	global mallet, cp
	mydir = os.path.abspath(os.path.dirname(__file__))
	c = ConfigFile(os.path.join(mydir, 'mallet.prop'))
	
	mallet = c['mallet']

	bsh = os.path.join(mallet, 'lib/bsh.jar')
	trv = os.path.join(mallet, 'lib/trove-2.0.2.jar')
	cls = os.path.join(mallet, 'class/')
	
	cp = '%s:%s:%s' % (bsh, trv, cls)
	

def train(train_path, model_path, out_f = sys.stdout, err_f = sys.stderr):
	setup()
	cmd = 'java -cp %s cc.mallet.fst.SimpleTagger ' % cp
	cmd += '--train true '
	cmd += '--default-label X '
	cmd += '--model-file %s ' % model_path
	cmd += '--threads 8 '
	#cmd += '--feature-induction true ' 
	cmd += '--viterbi-output true '
	#cmd += '--fully-connected false '
	#cmd += '--weights sparse '
	cmd += train_path
								
	# Write the command out
	err_f.write('#'*80+'\nTRAINING:\n'+'-'*80+'\n')
	err_f.write(re.sub('\s+', ' ', cmd)+'\n'+'-'*80+'\n')
	err_f.flush()
				
	p = sub.Popen(cmd.split(), stderr=sub.STDOUT, stdout=sub.PIPE)
	
	while p.poll() == None:
		out = p.stdout.read(1)#print(p.stderr.read(1))
		#out, err = p.communicate()
		#out_f.write(out.decode('utf-8'))
		err_f.write(out.decode('utf-8'))
		#out_f.flush()
		err_f.flush()
	
	
def test(test_path, model_path, out_f = sys.stdout, err_f = sys.stderr):
	setup()
	cmd = 'java -cp %s cc.mallet.fst.SimpleTagger ' % cp
	
	cmd += '--train false '
	cmd += '--test lab '
	cmd += '--default-label X '
	cmd += '--model-file %s ' % model_path
	cmd += '--threads 8 '
	
	cmd += test_path 
			
	# Write the command out
	err_f.write('#'*80+'\n'+'TESTING:\n'+'-'*80+'\n')
	err_f.write('%s\n' % re.sub('\s+', ' ', cmd))
	err_f.write('-'*80+'\n')
			
	p = sub.Popen(cmd.split(), stderr=sub.PIPE, stdout=sub.PIPE)
	
	# While the process hasn't responded
	while p.poll() == None:
		out, err = p.communicate()
		out_f.write(out.decode('utf-8'))
		err_f.write(err.decode('utf-8'))
		out_f.flush()
		err_f.flush()
		
def write_out(test_path, model_path, tag_out, out_f = sys.stderr, err_f = sys.stderr):
	setup()
	cmd = 'java -cp %s cc.mallet.fst.SimpleTagger ' % cp
	
	cmd += '--train false '
	cmd += '--default-label X '
	cmd += '--model-file %s ' % model_path
	cmd += '--threads 8 '
	cmd += '--n-best 4 '
	
	cmd += test_path
	
	p = sub.Popen(cmd.split(), stderr=sub.PIPE, stdout=sub.PIPE)
	
	while p.poll() == None:
		out, err = p.communicate()
		err_f.write(err.decode('utf-8'))
		err_f.flush()
		tag_out.write(out.decode('utf-8'))
		tag_out.flush()
	
	
def write_and_eval(test_path, model_path, out_path, out_f = sys.stdout, err_f = sys.stderr):
	tagged_f = open(out_path, 'w', encoding='utf-8')
	write_out(test_path, model_path, tagged_f, out_f, err_f)
	tagged_f.close()
	simple_tagger_eval(out_path, test_path, out_f = out_f)
	

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-c', '--conf', type=existsfile, required=True)
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	#===========================================================================
	# Log file setup
	#===========================================================================
	log_path = c.get('log_file')
	if log_path:
		f = open(log_path, 'w', encoding='utf-8')
		out_f = f
		err_f = f
	else:
		out_f = sys.stdout
		err_f = sys.stderr
		

	#===========================================================================
	# Train and Test
	#===========================================================================
	
	train(c['train_path'], c['model_path'], out_f, err_f)
	test(c['test_path'], c['model_path'], out_f, err_f)
	
	#===========================================================================
	# Also, write out the output.
	#===========================================================================
	
	output_path = c.get('output_path')
	if output_path:
		out_f.write('#'*80+'\nOUTPUTTING:\n'+'-'*80+'\n')
		write_and_eval(c['test_path'], c['model_path'], output_path, out_f, err_f)
	out_f.close()
	
