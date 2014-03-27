'''
Created on Mar 21, 2014

@author: rgeorgi
'''

import argparse
import glob
from utils.fileutils import globlist
from utils.string_utils import tokenize_string, tag_tokenizer
from utils.StatDict import StatDict

def gather_stats(filelist, tagged):
	words = StatDict()
	tags = StatDict()
	typetags = StatDict()
	
	for filename in filelist:
		f = open(filename, 'r')
		for line in f:
			tokens = tokenize_string(line, tokenizer=tag_tokenizer)
			for token in tokens:
				if token.seq not in words:
					typetags[token.label] += 1
				
				words[token.seq] += 1
				tags[token.label] += 1
				

		
	print('Tokens,Types,POS,Tokens,Types,%Tokens,%Types')		
	print(words.total, end=",")
	print(len(words), end=",")
	
	
	labels = list(tags.keys())
	labels = sorted(labels)
	for i, tag in enumerate(labels):
		tagcounts = tags[tag]
		typetagcounts = typetags[tag]
		
		percent_tokens = float(tagcounts) / words.total * 100
		percent_types = float(typetagcounts) / len(words)* 100	
		
		if i > 0:
			print(',,', end='')
		print('%s,%d,%d,%.2f,%0.2f' % (tag, tagcounts, typetagcounts, percent_tokens, percent_types))
	

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('file', nargs='+')
	p.add_argument('--tagged', default=True)
	
	args = p.parse_args()
	
	gather_stats(args.file, args.tagged)