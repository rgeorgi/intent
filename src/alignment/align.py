#!/usr/bin/env python
'''
Created on Feb 14, 2014

@author: rgeorgi
'''

import os, sys, re, argparse

from utils.ConfigFile import ConfigFile
from alignment.Alignment import Alignment, AlignedSent, AlignedCorpus
import nltk
from utils.listutils import all_indices

def heuristic_align_corpus(a_corpus, lowercase = True, remove_punc = True, stem = True, morph_on = True, aln_direction='a'):
	ha_corpus = AlignedCorpus()
	for a_sent in a_corpus:
		ha_sent = heuristic_align(a_sent, lowercase, remove_punc, stem, morph_on, aln_direction)
		ha_corpus.append(ha_sent)
	return ha_corpus

def remove_punctuation(s):
	return re.sub('\(.*?\)', '', s)

global stemmer 
stemmer = nltk.stem.snowball.EnglishStemmer()

def stem_token(st):
	try:
		return stemmer.stem(st)
	except UnicodeDecodeError as ude:
		sys.stderr.write('WARN: Stemming failed. on "%s" \n' % st)
		return st

def heuristic_align(a_sent, lowercase=True, remove_punc = True, stem = True, morph_on=True, aln_direction='a'):
	
	
	src_tokens = a_sent.src_tokens
	tgt_tokens = a_sent.tgt_tokens
	
	if lowercase:
		src_tokens = map(lambda s: s.lower(), src_tokens)
		tgt_tokens = map(lambda t: t.lower(), tgt_tokens)
		
	if remove_punc:
		src_tokens = map(remove_punctuation, src_tokens)
		tgt_tokens = map(remove_punctuation, tgt_tokens)
		
	if stem:
		src_tokens = map(stem_token, src_tokens)
		tgt_tokens = map(stem_token, tgt_tokens)
		
	
	alignments = Alignment()
	
	
# 	
# 	if aln_direction == 'a':
# 		for src_i in range(len(src_tokens)):
# 			src_token = src_tokens[src_i]
# 			
# 			if src_token in tgt_tokens:
# 				tgt_i = tgt_tokens.index(src_token)
# 				alignments.add((src_i+1, tgt_i+1))
# 			
# 			if morph_on:
# 				for morph in src_token.split('-'):
# 					if stem:
# 						morph = stem_token(morph)
# 					
# 					# Take the index that is in line with this one...
# 					tgt_indices = all_indices(morph, tgt_tokens)
# 					for tgt_i in tgt_indices:
# 						existing_pair = alignments.contains_tgt(tgt_i)
# 						
# 						# If the target token has already been assigned, skip it
# 						if alignments.contains_tgt(tgt_i):
# 							continue
# 						
# 						# Otherwise, assign left-to-right
# 						alignments.add((src_i+1, tgt_i+1))
# 						break
# 					
# 	elif aln_direction == 'b':
# 		for tgt_i in range(len(tgt_tokens)):
# 			tgt_token = tgt_tokens[tgt_i]
# 			
# 			if tgt_token in src_tokens:
# 				src_i = src_tokens.index(tgt_token)
# 				alignments.add((src_i+1, tgt_i+1))
# 				
# 			if morph_on:
# 				for morph in tgt_token.split('-'):
# 					if stem:
# 						morph = stem_token(morph)
# 					
# 					# Take the index that is in line with this one...
# 					src_indices = all_indices(morph, src_tokens)
# 					for src_i in src_indices:
# 						existing_pair = alignments.contains_tgt(tgt_i)
# 						
# 						# If the target token has already been assigned, skip it
# # 						if alignments.contains_src(src_i):
# # 							continue
# 						
# 						# Otherwise, assign left-to-right
# 						alignments.add((src_i+1, tgt_i+1))
# 						break
# 			
		
	
	return AlignedSent(a_sent.src_tokens, a_sent.tgt_tokens, alignments)
	

def align_lines(e_iter, f_iter):
	
	aln_corp = []
	
	while True:
		try:
			e_line = e_iter.next()
			f_line = f_iter.next()
		except StopIteration as si:
			break
				
		aln_sent = AlignedSent(words=e_line.split(), mots=f_line.split())
		aln_corp.append(aln_sent)
		
	e_iter.close(), f_iter.close()
	return aln_corp
# 	ibm = IBMModel1(aln_corp[:100])
# 	print ibm.aligned()
	
def align_files(e_file, f_file):
	e_f = open(e_file, 'r')
	f_f = open(f_file, 'r')
	return align_lines(iter(e_f), iter(f_f))


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('c', metavar='CONFIG')
	
	args = p.parse_args()
	
	c = ConfigFile(args.c)
	
	
	align_files(c['e_file'], c['f_file'])