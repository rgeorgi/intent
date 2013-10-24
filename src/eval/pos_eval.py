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

from optparse import OptionParser
from ConfigParser import ConfigParser
import re

__all__ = []
__version__ = 0.1
__date__ = '2013-08-26'
__updated__ = '2013-08-26'

def pos_eval(goldpath, testpath, delimeter):
	gold_f = file(goldpath, 'r')
	test_f = file(testpath, 'r')
	
	matches = 0
	tokens = 0
	sents = 0
	seen_tags = {}
	
	gold_lines = gold_f.readlines()
	test_lines = test_f.readlines()
	
	for test, gold in zip(test_lines, gold_lines):
		test_tokens = test.split()
		gold_tokens = gold.split()		
			
		# Make sure all the lines are of equal length
		if len(test_tokens) != len(gold_tokens):
			print test_tokens
			print gold_tokens
			raise Exception('lines of unequal length')
		
		sents += 1
		
		for test_token, gold_token in zip(test_tokens, gold_tokens):
			test_word, test_tag = re.search('^(.*)/(.*)$', test_token).groups()
			gold_word, gold_tag = re.search('^(.*)/(.*)$', gold_token).groups()
			
			seen_tags[test_tag] = True			
			
			assert test_word == gold_word
			
			if test_tag == gold_tag:
				matches += 1				
			tokens += 1
			
	tags = seen_tags.keys()
	
	print 'Tags: %d' % len(tags)
	print 'Tokens: %d' % tokens
	print 'Matches: %d' % matches
	print 'Sents: %d' % sents
	print 'Accuracy: %.2f' % (float(matches)*100 / tokens)
				

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
	parser.add_option("-c", "--conf", dest="conf", help="set input path [default: %default]", metavar="FILE")
	parser.add_option('-g', '--gold', dest='gold', help='Specify gold file without conf file.')
	parser.add_option('-t', '--test', dest='test', help='Specify test file without conf file.')
	parser.add_option('-d', '--delimeter', dest='delimeter', help='Specify the delimeter', default='/')
	
	# set defaults
	parser.set_defaults(outfile="./out.txt", infile="./in.txt")
	
	(opts, args) = parser.parse_args(argv)
	c = ConfigParser()
	
	if not opts.conf:
		if not opts.gold and opts.test:
			sys.stderr.write('Either the conf file or gold and opts file must be specified.')
			parser.print_help()
			sys.exit()
		else:
			gold = opts.gold
			test = opts.test
			delimeter = opts.delimeter
	else:
		c.read(opts.conf)
		gold = c.get('main', 'goldfile')
		test = c.get('main', 'testfile')
		delimeter = c.get('main', 'delimeter')
		
	
	pos_eval(gold, test, delimeter)
		


if __name__ == "__main__":
	main()