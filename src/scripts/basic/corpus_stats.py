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

def gather_stats(filelist, tagged):
	
	# Count of each unique word and its count.
	wordCount = StatDict()
	
	# Count of each unique tag and its count.
	tagCount = StatDict()
	
	# For each POS tag, the number of total
	# words used in that count.
	typetags = StatDict()
	
	# Count of each unique tag and the word types associated with it.
	tagtypes = defaultdict(set)
	
	for filename in filelist:
		f = open(filename, 'r', encoding='utf-8')
		for line in f:
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
 

	print('Total Tokens : %d' % wordCount.total)
	print('Total Types  : %d' % len(wordCount))
	print('Avg Tags/Type: %.2f' % tag_per_type_avg)

		
# 	print('Tokens,Types,POS,Tokens,Types,%Tokens,%Types')		
# 	print(wordCount.total, end=",")
# 	print(len(wordCount), end=",")
# 	
# 	
# 	labels = list(tagCount.keys())
# 	labels = sorted(labels)
# 	for i, tag in enumerate(labels):
# 		tagcounts = tagCount[tag]
# 		typetagcounts = typetags[tag]
# 		
# 		percent_tokens = float(tagcounts) / wordCount.total * 100
# 		percent_types = float(typetagcounts) / len(wordCount)* 100	
# 		
# 		if i > 0:
# 			print(',,', end='')
# 		print('%s,%d,%d,%.2f,%0.2f' % (tag, tagcounts, typetagcounts, percent_tokens, percent_types))
	
#===============================================================================
# MAIN
#===============================================================================

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('file', nargs='+')
	p.add_argument('--tagged', default=True)
	
	args = p.parse_args()
	
	gather_stats(args.file, args.tagged)