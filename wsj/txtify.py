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

__all__ = []
__version__ = 0.1
__date__ = '2013-08-26'
__updated__ = '2013-08-26'

DEBUG = 0
TESTRUN = 0
PROFILE = 0

def raw_writer(path, lines):
	f = file(path, 'w')
	for line in lines:
		f.write('%s\n' % line)
	f.close()




def parse_wsj(root, outdir, testfile, trainfile, goldfile, split = 90, maxlength = 10,
			delimeter='##', tagmap = None, remappedfile = None,
			start_section = 0, sentence_limit = 0):
	all_sents = []
	gold_sents = []
	remapped_sents = []
	
	if tagmap:
		tm = TagMap(path=tagmap)
	
	posdir = os.path.join(root, 'tagged/wsj')
	
	
	paths = map(lambda path: os.path.join(posdir, path), os.listdir(posdir))	
	dirs = filter(lambda dir: os.path.isdir(dir), paths)
	valid_dirs = filter(lambda dir: int(os.path.basename(dir)) >= start_section, dirs)
	
	pos_files = []
	
	for valid_dir in valid_dirs:
		for root, dir, files in os.walk(valid_dir):
			
			for path in filter(lambda x: x.startswith('wsj_'), files):
				path = os.path.join(root, path)
				pos_files.append(path)
			
	finish_processing = False
	
	# --) Number of sentences before bailing
	sentence_count = 0
	
	for path in pos_files:			
		f = file(path, 'r')
		data = f.read()
		stories = re.split('={38}', data)
		stories = filter(lambda story: story.strip(), stories)
		
		for story in stories:
			story_str = ''
			gold_str = ''
			remapped_str = ''
			
			token_count = 0
			# Remove bracketing.
			story = re.sub('[\[\]]', '', story)
			
			# Remove multiple lines.
			story = re.sub('\s+', ' ', story)
			
			# tokenize on remaining whitespace.
			tokens = re.split('\s+', story)
			
			for token in filter(lambda token: token.strip(), tokens):
				word, tag = re.search('^(.*)/(.*)$', token.strip()).groups()
				
				# For tags such as VBG|NN, take only the first.	
				tag = tag.split('|')[0]					
								
				story_str += '%s ' % word
				gold_str += '%s%s%s ' % (word, delimeter, tag)
				if tagmap:
					newtag = tm[tag]
					remapped_str += '%s%s%s ' % (word, delimeter, newtag)
					
				token_count += 1
				
			if token_count <= maxlength:
				all_sents.append(story_str.strip())
				gold_sents.append(gold_str.strip())
				remapped_sents.append(remapped_str.strip())
				
				sentence_count += 1
				
				if sentence_count >= sentence_limit:
					finish_processing = True
					
			if finish_processing:
				break
		if finish_processing:
			break
					
	# Split the data into train and test.
	train_idx = int(len(all_sents) * (float(split)/100))
	train_sents = all_sents[:train_idx]
	test_sents = all_sents[train_idx:]
	gold_out = gold_sents[train_idx:]
	remapped_out = remapped_sents[train_idx:]
	
	raw_writer(os.path.join(outdir, testfile), test_sents)
	raw_writer(os.path.join(outdir, trainfile), train_sents)
	raw_writer(os.path.join(outdir, goldfile), gold_out)
	if remappedfile:
		raw_writer(os.path.join(outdir, remappedfile), remapped_out)
			
			
		

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
	c = ConfigParser.ConfigParser(defaults={'tagmap':None, 'remappedfile':None, 'start_section':2,'sentence_limit':2000})
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