#!/usr/bin/env python
# encoding: utf-8
'''
igt.odin -- parser for 2013 ODIN data

igt.odin is a parser

It defines an input reader that outputs IGT instances

@author:     rgeorgi@uw.edu
			
@copyright:  2013 Ryan Georgi. All rights reserved.
			
@license:    MIT License

@contact:    rgeorgi@uw.edu
@deffield    updated: Updated
'''

import sys
import os
import re
from utils.ConfigFile import ConfigFile

import argparse
from utils.fileutils import matching_files
from igt.IGTFile import IGTFile

def extract_glosses(indir, glossout, transout):
	igt_paths = matching_files(indir, '[a-z]{3}\.txt$', recursive=True)
	igt_files = [IGTFile(f) for f in igt_paths]
	
	glossf = file(glossout, 'w')
	transf = file(transout, 'w')
	
	written = 0
	for igtf in igt_files:
		for instance in igtf.instances:
			if instance.gloss and instance.trans:				
				glossf.write(instance.gloss+'\n')
				transf.write(instance.trans+'\n')
				written += 1
	print '%d instances written.' % written
	
	

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('config', metavar='CONFIG')	
	
	args = p.parse_args()
	
	c = ConfigFile(args.config)
	
	extract_glosses(c['odin_dir'],
					c['gloss_out'],
					c['trans_out'])