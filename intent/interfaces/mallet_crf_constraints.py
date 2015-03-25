'''
Created on Mar 6, 2014

@author: rgeorgi
'''

# Global imports ---------------------------------------------------------------
import argparse, os, sys
import subprocess as sub

# Internal Imports -------------------------------------------------------------
from intent.utils.ConfigFile import ConfigFile
from intent.interfaces.mallet_crf import write_and_eval


def setup():
	global mallet, cp
	mydir = os.path.abspath(os.path.dirname(__file__))
	c = ConfigFile(os.path.join(mydir, 'mallet.prop'))
	
	mallet = c['mallet']

	bsh = os.path.join(mallet, 'lib/bsh.jar')
	trv = os.path.join(mallet, 'lib/trove-2.0.2.jar')
	cls = os.path.join(mallet, 'class/')
	
	cp = '%s:%s:%s' % (bsh, trv, cls)
	

def train(train_path, test_path, constraint_path, model_path, log_path = sys.stdout):
	setup()
	
	cmd = 'java -Xmx4096m -cp %s cc.mallet.fst.semi_supervised.tui.SimpleTaggerWithConstraints' % (cp)
	
	cmd += ' --train true'
	cmd += ' --default-label X'
	cmd += ' --model-file %s' % model_path
	cmd += ' --threads 8'
	cmd += ' --learning ge'
	cmd += ' --test lab'
	cmd += ' --orders 0,1'
	cmd += ' --penalty kl'
# 	cmd += ' --training-proportion 0.5'
# 	cmd += ' --gaussian-variance 60.0'
#	cmd += ' --q-gaussian-variance 100.0'
# 	cmd += ' --n-best 2'
# 	cmd += ' --continue-training true'
# 	cmd += ' --help true'	
	cmd += ' %s %s %s' % (train_path, test_path, constraint_path)
	
	log_path.write(cmd+'\n')
	log_path.flush()
# 	sys.exit()

	p = sub.Popen(cmd.split(), stderr=sub.PIPE, stdout=sub.PIPE)
	
	while p.poll() == None:
		out = p.stdout.read(1)
		
		log_path.write(out.decode('utf-8'))
		
		log_path.flush()
		
	log_path.close()


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-c', '--conf', help='Configuration file.')
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	log_f = sys.stdout
	if c.get('log_path'):
		log_f = open(c.get('log_path'), 'w', encoding='utf-8')
	
	train(c['train_path'], c['test_path'], c['constraint_path'], c['model_path'], log_f)
	
	write_and_eval(c['test_path'], c['model_path'], c['output_path'])
		