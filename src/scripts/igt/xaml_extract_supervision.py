'''
Created on Apr 30, 2014

@author: rgeorgi
'''

from ingestion.xaml import XamlParser
from argparse import ArgumentParser
from glob import glob
import os
from utils.argutils import existsdir, existsfile
import pickle

import logging
from utils.ConfigFile import ConfigFile

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--conf', dest='conf', type=existsfile, required=True)
	p.add_argument('-v', dest='verbose', help="Verbosity level", default=0, action='count')
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	#===========================================================================
	# Logging
	#===========================================================================
	
	if args.verbose == 1:
		logging.basicConfig(level=logging.WARN)
	elif args.verbose == 2:
		logging.basicConfig(level=logging.INFO)
	elif args.verbose >= 3:
		logging.basicConfig(level=logging.DEBUG)
	
	#===========================================================================
	# Set up the output paths for the gram stuff.
	#===========================================================================
	
	outdir = c.get('outdir', t=existsdir, default=os.getcwd())
	
	tagger_output = os.path.join(outdir, 'gloss_tags.txt')
	ltagger_output = os.path.join(outdir, 'lang_tags.txt')
	ptagger_output = os.path.join(outdir, 'lang_tags_proj.txt')
	
	classifier_output = os.path.join(outdir, 'gloss_feats.txt')
	
		
	if c.get('posdict'):
		c['posdict'] = pickle.load(open(c.get('posdict'), 'rb'))
		
	c['tag_out'] = tagger_output
	c['class_out'] = classifier_output
	
	#===========================================================================
	# Now parse the files
	#===========================================================================
	
	xp = XamlParser.XamlParser(**c)
	
	

	c['tag_f'] = open(c.get('tag_out'), 'w', encoding='utf-8')
	c['class_f'] = open(c.get('class_out'), 'w', encoding='utf-8')
	
	xml_files = glob(os.path.join(c.get('input_dir'), c.get('pattern', default='*.xml')))

	for x_f in xml_files:
		xp.parse(x_f, **c)