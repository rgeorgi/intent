'''
Created on Nov 26, 2014

@author: rgeorgi
'''
from argparse import ArgumentParser
from utils.argutils import existsfile, writefile
from interfaces.MalletMaxentTrainer import MalletMaxentTrainer
from utils.ConfigFile import ConfigFileException, ConfigFile
import sys

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--conf', type=existsfile, required=True)
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	mmt = MalletMaxentTrainer()
	mmt.train_txt(c.get('feat_path', t=existsfile), c.get('model_path'), c.get('log_path', sys.stdout, t=writefile))
	