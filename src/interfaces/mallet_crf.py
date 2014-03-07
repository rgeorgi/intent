'''
Created on Mar 6, 2014

@author: rgeorgi
'''

import argparse
from utils.ConfigFile import ConfigFile
import os
import sys

def train_crf(mallet_root, train_path, test_path, constraint_path, model_path):
	classpath = '%s/class:%s/lib/bsh.jar:%s/lib/trove-2.0.2:%s/lib/mallet-deps.jar' % ((mallet_root,)*4)

	cmd = 'java -Xmx2048m -cp %s cc.mallet.fst.semi_supervised.tui.SimpleTaggerWithConstraints' % (classpath)
	
	cmd += ' --train true'
	cmd += ' --default-label UNK'
	cmd += ' --model-file %s' % model_path
	cmd += ' --threads 8'
	cmd += ' --learning pr'
	cmd += ' --test lab'
	cmd += ' --orders 0,1'
	cmd += ' --penalty l2'
# 	cmd += ' --training-proportion 0.5'
# 	cmd += ' --gaussian-variance 60.0'
	cmd += ' --q-gaussian-variance 100.0'
# 	cmd += ' --n-best 2'
# 	cmd += ' --continue-training true'
# 	cmd += ' --help true'	
	cmd += ' %s %s %s' % (train_path, test_path, constraint_path)
	
	sys.stderr.write(cmd+'\n')
# 	sys.exit()

	os.system(cmd) 


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('conf', help='Configuration file.')
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	train_crf(c['mallet_root'], c['train_path'], c['test_path'], c['constraint_path'], c['model_path'])