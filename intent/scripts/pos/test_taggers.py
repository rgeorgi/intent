'''
Created on Jul 21, 2014

@author: rgeorgi
'''

from argparse import ArgumentParser
import interfaces.stanford_tagger as tag
from utils.argutils import existsfile
from utils.ConfigFile import ConfigFile
from eval.pos_eval import slashtags_eval

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--conf', required=True, type=existsfile)
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)

	tag.train(c['train_path'],c['model_path'])
	tag.test(c['test_path'], c['model_path'], c['out_path'])
	
	slashtags_eval(c['test_path'], c['out_path'], c['delimeter'])