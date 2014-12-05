'''
Created on Nov 21, 2014

@author: rgeorgi
'''

import argparse
from argparse import ArgumentParser
from utils.argutils import existsfile
from utils.ConfigFile import ConfigFile
from ingestion.xaml.XamlParser import XamlProcessor
import sys
from interfaces.mallet_maxent import MalletMaxent
import pickle
import os

def process_xaml_file(in_path, **kwargs):
	xp = XamlProcessor(**kwargs)
	
	# Process only lines with L,G,T
	xp.add_lgt_filter()
	
	# Build an IGT Corpus...
	xp.add_igt_corpus_filter()
	
	# Initialize the MaxentClassifier
	mc = MalletMaxent(kwargs['classifier_path'])
	
	
	xp.parse(in_path)
	
	corpus = xp['igt_corpus']
	
		
	pc = corpus.classifier_pos_corpus(mc, **kwargs)
	
	os.makedirs(os.path.dirname(kwargs.get('output_path')), exist_ok=True)
	
	pc.write(kwargs['output_path'], 'slashtags')
	

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--conf', required=True, type=existsfile)
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	if c.get('posdict'):
		c['posdict'] = pickle.load(open(c.get('posdict'), 'rb'))
	
	# Process the arguments
	in_path = c.get('input_path', t=existsfile)
	process_xaml_file(in_path, **c)
	