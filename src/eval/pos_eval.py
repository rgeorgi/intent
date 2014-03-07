#!/usr/bin/env python
# encoding: utf-8
'''
eval.pos_eval -- pos tag evaluator

eval.pos_eval is a script to evaluate pos-tagged files.

It defines a main method that scores tag accuracy.

@author:     Ryan Georgi
			
@copyright:  2013 Ryan Georgi. All rights reserved.
			
@license:    MIT License

@contact:    rgeorgi@uw.edu
@deffield    updated: Updated
'''

import sys
import os

from argparse import ArgumentParser
from utils import ConfigFile
import re
from eval.EvalException import POSEvalException
from pos.TagMap import TagMap
from utils.encodingutils import getencoding

__all__ = []
__version__ = 0.1
__date__ = '2013-08-26'
__updated__ = '2013-08-26'

def pos_eval(goldpath, testpath, delimeter, tagmap=None):
	if not goldpath:
		raise POSEvalException('Gold Path not set.')
	if not testpath:
		raise POSEvalException('Test path not set.')
			
	gold_f = open(goldpath, 'r')
	test_f = open(testpath, 'r')
	
	matches = 0
	tokens = 0
	sents = 0
	remapped_matches = 0
	seen_tags = {}
	
	gold_lines = gold_f.readlines()
	test_lines = test_f.readlines()
	
	if tagmap:
		tm = TagMap(tagmap)
	
	for test, gold in zip(test_lines, gold_lines):
		test_tokens = test.split()
		gold_tokens = gold.split()		
			
		# Make sure all the lines are of equal length
		if len(test_tokens) != len(gold_tokens):
			print(test_tokens)
			print(gold_tokens)
			raise POSEvalException('lines of unequal length')
		
		
		sents += 1
		
		for test_token, gold_token in zip(test_tokens, gold_tokens):
			test_word, test_tag = re.search('^(.*)/(.*)$', test_token).groups()
			gold_word, gold_tag = re.search('^(.*)/(.*)$', gold_token).groups()
			
			if tagmap:
				test_remapped = tm[test_tag]
				gold_remapped = tm[gold_tag]
				if test_remapped == gold_remapped:
					remapped_matches += 1
			
			seen_tags[test_tag] = True			
			
# 			if test_word != gold_word:
# 				raise POSEvalException('Words %s and %s do not match.' % (test_word, gold_word))
			
			
			if test_tag == gold_tag:
				matches += 1				
			tokens += 1
			
	tags = seen_tags.keys()
	
	print('Tags: %d' % len(tags))
	print('Tokens: %d' % tokens)
	print('Matches: %d' % matches)
	print('Sents: %d' % sents)
	print('Accuracy: %.2f' % (float(matches)*100 / tokens))
	if tagmap:
		print('Remapped Accuracy: %.2f' % (float(remapped_matches)*100/tokens))
				

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
	parser = ArgumentParser()
	parser.add_argument("-c", "--conf", dest="conf", help="set input path [default: %default]", metavar="FILE")
	parser.add_argument('-g', '--gold', dest='gold', help='Specify gold file without conf file.')
	parser.add_argument('-t', '--test', dest='test', help='Specify test file without conf file.')
	parser.add_argument('-d', '--delimeter', dest='delimeter', help='Specify the delimeter', default='/')
	
	# set defaults
	parser.set_defaults(outfile="./out.txt", infile="./in.txt")
	
	args = parser.parse_args()
	

	if not args.conf:
		if not args.gold and args.test:
			sys.stderr.write('Either the conf file or gold and opts file must be specified.')
			parser.print_help()
			sys.exit()
		else:
			gold = args.gold
			test = args.test
			delimeter = args.delimeter
	else:
		c = ConfigFile.ConfigFile(args.conf)
		gold = c['goldfile']
		test = c['testfile']
		delimeter = c['delimeter']
		tagmap = c['tagmap']
		
	if gold and test and delimeter:
		pos_eval(gold, test, delimeter, tagmap)
	else:
		sys.stderr.write('Arguments missing.')
		sys.exit()
		
		


if __name__ == "__main__":
	main()