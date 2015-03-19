'''
Created on Oct 1, 2014

@author: rgeorgi
'''
from interfaces.MalletMaxentTrainer import MalletMaxentTrainer
from utils.ConfigFile import ConfigFile
import glob
import os
from ingestion.xaml.XamlParser import XamlParser, XamlProcessor
from utils.argutils import ArgPasser, existsfile
import pickle
from collections import OrderedDict
from multiprocessing import Pool
from argparse import ArgumentParser

		

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--conf', required=True, type=existsfile)
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)

	#===========================================================================
	# 1) Start by extracting the features for the training of the classifier...
	#===========================================================================
	# Load the part-of-speech dictionary...
	if c.get('posdict'):
		c['posdict'] = pickle.load(open(c.get('posdict'), 'rb'))

	xp = XamlProcessor()
	xp.add_igt_corpus_filter()
	xp.add_gram_output_filter(c['class_out'])
	
	
	xml_files = glob.glob(os.path.join(c.get('input_dir'), c.get('pattern', default='*.xml')))
	for f in xml_files:
		xp.add_file(f)
	xp.parse_all()
	
	# Close the feature file
	xp.kwargs['class_f'].close()
	
	#===========================================================================
	# 
	#===========================================================================
	
	mmt = MalletMaxentTrainer()
	mmt.train_txt(c.get('class_out'), c.get('model_path'))
	