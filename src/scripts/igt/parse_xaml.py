'''
Created on Apr 30, 2014

@author: rgeorgi
'''

from treebanks.xaml import XamlParser
from argparse import ArgumentParser
from glob import glob
import os
import sys
import xml.sax

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('dir', metavar='DIR', nargs='+')
	p.add_argument('-o', '--outdir', default=os.getcwd())
	p.add_argument('--pattern', default='[a-z][a-z][a-z].xml')
	p.add_argument('--lowercase', action='store_true', default=False)
	
	args = p.parse_args()
	
	#===========================================================================
	# Set up the output paths for the gram stuff.
	#===========================================================================
	
	tagger_output = os.path.join(args.outdir, 'gloss_tags.txt')
	ltagger_output = os.path.join(args.outdir, 'lang_tags.txt')
	ptagger_output = os.path.join(args.outdir, 'lang_tags_proj.txt')
	
	classifier_output = os.path.join(args.outdir, 'gloss_feats.txt')
	
	
	kwargs = vars(args)
	
	kwargs['tag_out'] = open(tagger_output, 'w')
	kwargs['ltag_out'] = open(ltagger_output, 'w')
	kwargs['class_out'] = open(classifier_output, 'w')
	
	#===========================================================================
	# Now parse the files
	#===========================================================================
	
	xp = XamlParser.XamlParser()
	for dir in args.dir:
		xml_files = glob(os.path.join(dir, args.pattern))
		for x_f in xml_files:				
			xp.parse(x_f, **kwargs)