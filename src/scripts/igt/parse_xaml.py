'''
Created on Apr 30, 2014

@author: rgeorgi
'''

from treebanks.xaml import XamlParser
from argparse import ArgumentParser
from glob import glob
import os
import sys
from utils.commandline import existsdir, existsfile
import pickle
from collections import defaultdict

import shelve
from utils.TwoLevelCountDict import TwoLevelCountDict
import logging

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('dir', metavar='DIR', nargs='+', type=existsdir)
	p.add_argument('-o', '--outdir', default=os.getcwd(), type=existsdir)
	p.add_argument('--pattern', default='[a-z][a-z][a-z].xml')
	p.add_argument('--lowercase', action='store_true', default=False)
	p.add_argument('--posdict', dest='posdict', type=existsfile)
	p.add_argument('--log', action="store_true")
	
	args = p.parse_args()
	
	#===========================================================================
	# Logging
	#===========================================================================
	if args.log:
		pass
		#logging.basicConfig(level=logging.DEBUG)
	
	#===========================================================================
	# Set up the output paths for the gram stuff.
	#===========================================================================
	
	tagger_output = os.path.join(args.outdir, 'gloss_tags.txt')
	ltagger_output = os.path.join(args.outdir, 'lang_tags.txt')
	ptagger_output = os.path.join(args.outdir, 'lang_tags_proj.txt')
	
	classifier_output = os.path.join(args.outdir, 'gloss_feats.txt')
	
	kwargs = vars(args)
	
	if args.posdict:
		kwargs['posdict'] = pickle.load(open(args.posdict, 'rb'))
		
	kwargs['tag_out'] = tagger_output
	kwargs['class_out'] = classifier_output
	
	#===========================================================================
	# Now parse the files
	#===========================================================================
	
	xp = XamlParser.XamlParser(**kwargs)
	
	kwargs['tag_f'] = open(kwargs.get('tag_out'), 'w')
	kwargs['class_f'] = open(kwargs.get('class_out'), 'w')
	
	for dir in args.dir:
		xml_files = glob(os.path.join(dir, args.pattern))
		for x_f in xml_files:
			xp.parse(x_f, **kwargs)