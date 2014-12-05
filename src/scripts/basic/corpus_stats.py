'''
Created on Mar 21, 2014

@author: rgeorgi

Scripts for gathering general information on the various POS corpora being used. 

Basic analysis such as word types, number of types of POS tag, and the percentage
that each make up of things.
'''

import argparse
import glob
from utils.fileutils import globlist
from utils.StatDict import StatDict
from utils.token import tokenize_string, tag_tokenizer
from _collections import defaultdict
from utils.argutils import writefile
import sys

def gather_stats(filelist, tagged, log_file = sys.stdout, csv=False):
	
	# Count of each unique word and its count.
	wordCount = StatDict()
	
	# Count of each unique tag and its count.
	tagCount = StatDict()
	
	# For each POS tag, the number of total
	# words used in that count.
	typetags = StatDict()
	
	# Count of each unique tag and the word types associated with it.
	tagtypes = defaultdict(set)
	
	# Count the number of lines
	lines = 0
	
	for filename in filelist:
		f = open(filename, 'r', encoding='utf-8')
		for line in f:
			lines += 1
			tokens = tokenize_string(line, tokenizer=tag_tokenizer)
			for token in tokens:
				
				seq = token.seq.lower()
				
				if seq not in wordCount:
					typetags[token.label] += 1
				
				wordCount[seq] += 1
				tagCount[token.label] += 1
				
				# Start counting the average types per tag.
				tagtypes[seq] |= set([token.label])
				
				
	# Calculate tags per type
	type_sum = 0.
	for word in tagtypes.keys():
		type_sum += len(tagtypes[word])
		
	tag_per_type_avg = type_sum / len(tagtypes)

	#===========================================================================
	# Get the stats we want to return
	#===========================================================================

	total_tokens = wordCount.total
	total_types = len(wordCount)
	
	if not csv:
		log_file.write('Sentences    : %d\n' % lines)
		log_file.write('Total Tokens : %d\n' % total_tokens)
		log_file.write('Total Types  : %d\n' % total_types)
		log_file.write('Avg Tags/Type: %.2f\n' % tag_per_type_avg)
	else:
		log_file.write('sents,tokens,types,tags-per-type\n')
		log_file.write('%s,%s,%s,%.2f\n' % (lines, total_tokens, total_types, tag_per_type_avg))

	
	log_file.write('\n'* 2 + '='*80 + '\n')
	
	labels = list(tagCount.keys())
	labels = sorted(labels)
	
	
	log_file.write('tag, tag_counts, types_per_tag, percent_of_tokens, percent_of_types\n')
	for i, tag in enumerate(labels):
		tagcounts = tagCount[tag]
		typetagcounts = typetags[tag]
		
		percent_tokens = float(tagcounts) / wordCount.total * 100
		percent_types = float(typetagcounts) / len(wordCount)* 100	
		
		log_file.write('%s,%d,%d,%.2f,%0.2f\n' % (tag, tagcounts, typetagcounts, percent_tokens, percent_types))
	
#===============================================================================
# MAIN
#===============================================================================

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('file', nargs='+')
	p.add_argument('--tagged', default=True)
	p.add_argument('--log', default=sys.stdout, type=writefile)
	p.add_argument('--csv', action='store_true', default=True)
	
	args = p.parse_args()
	
	gather_stats(args.file, args.tagged, log_file = args.log, csv=args.csv)