#!/usr/bin/env python
# encoding: utf-8
'''
eval.slashtags_eval -- pos tag evaluator

eval.slashtags_eval is a script to evaluate pos-tagged files.

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
from eval.EvalException import POSEvalException, EvalException
from utils.TwoLevelCountDict import TwoLevelCountDict, POSEvalDict
from corpora.POSCorpus import POSCorpus

__all__ = []
__version__ = 0.1
__date__ = '2013-08-26'
__updated__ = '2013-08-26'




#===============================================================================
# 
#===============================================================================

def slashtags_eval(goldpath, testpath, delimeter, out_f=sys.stdout, tagmap=None):
			
	gold_c = POSCorpus.read_slashtags(goldpath)
	test_c = POSCorpus.read_slashtags(testpath)
	
	poseval(test_c, gold_c, out_f)

#===============================================================================
# 
#===============================================================================

def simple_tagger_eval(eval_path, gold_path, out_f = sys.stdout, csv=True):
	

	eval_c = POSCorpus.read_simpletagger(eval_path)
	gold_c = POSCorpus.read_simpletagger(gold_path)
	
	poseval(eval_c, gold_c, out_f)
	
	
def poseval(eval_sents, gold_sents, out_f = sys.stdout, csv=True, ansi=False, greedy_1_to_1=False, greedy_n_to_1=False, matrix=False):
	if len(eval_sents) != len(gold_sents):
		raise EvalException('Number of eval sents does not match number of gold sents.')
	
	#===========================================================================
	# Set up counters
	#===========================================================================
	c = POSEvalDict()
	d = POSEvalDict()
	
	i = 1
	
	for eval_sent, gold_sent in zip(eval_sents, gold_sents):
		
		# Check whether the whole sentence is correct.
		sent_correct = True
		
		if len(eval_sent) != len(gold_sent):
			raise EvalException('Number of tokens for sent #%d is unequal' % i)
		
		for eval_token, gold_token in zip(eval_sent, gold_sent):
			
			gold_label = str(gold_token.label)
			eval_label = str(eval_token.label)
			
			# Kludgy way to make sure all the assigned
			# labels end up getting seen.
			c[eval_label].add(eval_label, 0)
			
			c[gold_label].add(eval_label, 1)
			d[eval_label].add(gold_label, 1)
			
			# If one of the labels does not match,
			# the sentence does not match.
			if gold_label != eval_label:
				sent_correct = False
				
		# If the sentence matches it, count it...
	
	
	#===========================================================================
	# Now, evaluate based on the gold-to-eval labels
	#===========================================================================
	eval_print_helper(out_f, 'STANDARD', matrix, c, ansi, csv)

	
	if greedy_1_to_1:
		c.greedy_1_to_1()
		eval_print_helper(out_f, 'GREEDY 1-to-1',  matrix, c, ansi, csv)
		
	if greedy_n_to_1:
		c.greedy_n_to_1()
		eval_print_helper(out_f, 'GREEDY N-to-1', matrix, c, ansi, csv)
		
	return c

			
def eval_print_helper(out_f, title, matrix, c, ansi, csv):
	out_f.write('='*80+'\n')
	out_f.write('%s:\n' % title + '-'*80+'\n')
	if matrix:
		out_f.write(c.error_matrix(ansi=ansi, csv=csv))
		out_f.write('-'*80+'\n')
	out_f.write('OVERALL ACCURACY: %.2f\n' % c.accuracy() + '='*80+'\n')
	
	
	

if __name__ == '__main__':

	# setup option parser
	parser = ArgumentParser()
	parser.add_argument("-c", "--conf", dest="conf", help="set input path [default: %default]", metavar="FILE")
	parser.add_argument('-g', '--gold', dest='gold', help='Specify gold file without conf file.')
	parser.add_argument('-t', '--test', dest='test', help='Specify test file without conf file.')
	parser.add_argument('-d', '--delimeter', dest='delimeter', help='Specify the delimeter', default='/')
	
	# set defaults		
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
		delimeter = c.get('delimeter', '/')
		
		# Default to no tagmap, unless
		# specified in the config file.
		tagmap = c.get('tagmap')
		
	if gold and test and delimeter:
		slashtags_eval(gold, test, delimeter, tagmap)
	else:
		sys.stderr.write('Arguments missing.')
		sys.exit()
		