#!/usr/bin/env python
# encoding: utf-8
'''
wsj.txtify -- a WSJ-to-raw-text converter with.

wsj.txtify is a WSJ-to-raw-text converter

It defines a simple parser method.

@author:     Ryan Georgi
			
@copyright:  2013 Ryan Georgi. All rights reserved.
			
@license:    MIT License

@contact:    rgeorgi@uw.edu
@deffield    updated: Updated
'''

import sys
import os, glob
import ConfigParser
from utils.commandline import require_opt

from optparse import OptionParser
import re
from pos.TagMap import TagMap
from trees.ptb import parse_ptb_file
from treebanks.common import process_tree, write_files
from utils.systematizing import notify

__all__ = []
__version__ = 0.1
__date__ = '2013-08-26'
__updated__ = '2013-08-26'

DEBUG = 0
TESTRUN = 0
PROFILE = 0





def parse_wsj(root, outdir, testfile, trainfile, goldfile, split = 90, maxlength = 10,
			delimeter='##', tagmap = None, remappedfile = None,
			start_section = 0, sentence_limit = 0):
	all_sents = []
	gold_sents = []
	
	tm = None
	if tagmap:
		tm = TagMap(path=tagmap)
	
	posdir = os.path.join(root, 'combined/wsj')
	
	
	paths = map(lambda path: os.path.join(posdir, path), os.listdir(posdir))	
	dirs = filter(lambda dir: os.path.isdir(dir), paths)
	valid_dirs = filter(lambda dir: int(os.path.basename(dir)) >= start_section, dirs)
	
	pos_files = []
	
	for valid_dir in valid_dirs:
		for root, dir, files in os.walk(valid_dir):
			
			for path in filter(lambda x: x.startswith('wsj_'), files):
				path = os.path.join(root, path)
				pos_files.append(path)
			
	
	# --) Number of sentences before bailing
	sentence_count = 0
	
	finished_processing = False
	
	for path in pos_files:			
		trees = parse_ptb_file(path)
		
		# Now process each tree
		for tree in trees:
			sent_str, gold_str =  process_tree(tree, delimeter, maxlength, tm)
			if sent_str:						
				all_sents.append(sent_str)
				gold_sents.append(gold_str)
						
				sentence_count += 1
				if sentence_count >= sentence_limit:
					finished_processing = True
					break
			
		if finished_processing:
			break
				
	write_files(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents)
	notify()
					

			
			
		

def main(argv=None):
	'''Command line options.'''
	
	program_name = os.path.basename(sys.argv[0])
	program_version = "v0.1"
	program_build_date = "%s" % __updated__
	
	program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
	#program_usage = '''usage: spam two eggs''' # optional - will be autogenerated by optparse
	program_longdesc = '''''' # optional - give further explanation about what the program does
	program_license = "Copyright 2013 Ryan Georgi (Ryan Georgi)                                            \
				Licensed under the Apache License 2.0\nhttp://www.apache.org/licenses/LICENSE-2.0"
	
	if argv is None:
		argv = sys.argv[1:]

	# setup option parser
	parser = OptionParser(version=program_version_string, epilog=program_longdesc, description=program_license)
	parser.add_option("-c", "--conf", dest="conf", help="set conf file [default: %default]", metavar="FILE")
		
	# set defaults
	parser.set_defaults()
	
	# process options
	(opts, args) = parser.parse_args(argv)
	
	errors = require_opt(opts.conf, "Please specify the configuration file with -c or --conf", True)
		
	if errors:
		raise Exception("There were errors found in processing.")
	
	# MAIN BODY #
	c = ConfigParser.ConfigParser(defaults={'tagmap':None, 'remappedfile':None, 'start_section':'2','sentence_limit':'2000'})
	c.read(opts.conf)
	parse_wsj(c.get('wsj', 'root'), c.get('wsj', 'outdir'), c.get('wsj', 'testfile'), 
			c.get('wsj', 'trainfile'), c.get('wsj', 'goldfile'), c.getint('wsj', 'trainsplit'), 
			c.getint('wsj', 'maxlength'), c.get('wsj', 'delimeter'),
			c.get('wsj', 'tagmap'), c.get('wsj', 'remappedfile'),
			c.getint('wsj', 'start_section'),
			c.getint('wsj', 'sentence_limit'))
	
		


if __name__ == "__main__":
	if DEBUG:
		sys.argv.append("-h")
	if TESTRUN:
		import doctest
		doctest.testmod()
	if PROFILE:
		import cProfile
		import pstats
		profile_filename = 'wsj.txtify_profile.txt'
		cProfile.run('main()', profile_filename)
		statsfile = open("profile_stats.txt", "wb")
		p = pstats.Stats(profile_filename, stream=statsfile)
		stats = p.strip_dirs().sort_stats('cumulative')
		stats.print_stats()
		statsfile.close()
		sys.exit(0)
	sys.exit(main())