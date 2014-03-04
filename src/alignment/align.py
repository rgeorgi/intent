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

def morphfilter(m):
	for elt in m:
		if elt.lower() in ['acc', 'dat', 'inf']:
			m = m - set([elt])
	return m

class Morph(set):
	
	def __init__(self, seq, stem=True):
		seq = map(lambda s: s.strip(), seq)
		if stem:
			seq = map(stem_token, seq)
			
		super(Morph, self).__init__(seq)
		self = morphfilter(self)
	
	def __eq__(self, o):
		
		for elt in o:
			if elt in self:
				return True
		return False
	
	def __str__(self):
		elts = ''
		for elt in self:
			elts += str(elt)+' '
		return '<Morph: %s>' % (elts.strip())
		

def heur_match(s_i, src_seq, tgt_seq, stem = True):
	
	alignments = Alignment()
	
	src_morphs = map(lambda m: Morph(re.split('[\-\.]', m), stem=True), src_seq)
	tgt_morphs = map(lambda m: Morph(re.split('[\-\.]', m), stem=True), tgt_seq)
	
	
	
	s = src_morphs[s_i]
	
	src_matches = all_indices(s, src_morphs)
	tgt_matches = all_indices(s, tgt_morphs)
	
	
	
	# If there's only one src index, project it to all matches.
	if len(src_matches) == 1:
		for t_i in tgt_matches:
			alignments.add((s_i, t_i))
	
	# If the number of indices are equal, then go left-to-right		
	elif len(src_matches) == len(tgt_matches):
		pairs = zip(src_matches, tgt_matches)
		for pair in pairs:
			alignments.add(pair)
	
	# Finally, if there are more than one, but they are unequal...		
	elif len(src_matches) and len(tgt_matches):
		pairs = zip(src_matches, tgt_matches)
		for pair in pairs:
			alignments.add(pair)

	
	return alignments

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
	

# 	if aln_direction == 'a':
# 		
# 		# Step through each one of the source tokens...
# 		for src_i in range(len(src_tokens)):
# 			new_aligns = heur_match(src_i, src_tokens, tgt_tokens)
# 			for na in new_aligns:
# 				alignments.add(na)
# 				
# 	elif aln_direction == 'b':
# 		for tgt_i in range(len(tgt_tokens)):
# 			new_aligns = heur_match(tgt_i, tgt_tokens, src_tokens)
# 			for na in new_aligns:
# 				alignments.add(na)
# 		alignments = alignments.flip()
				

	if aln_direction == 'a':
		for src_i in range(len(src_tokens)):
			src_token = src_tokens[src_i]
			
			if src_token in tgt_tokens:
				tgt_i = tgt_tokens.index(src_token)
				alignments.add((src_i+1, tgt_i+1))
			
			if morph_on:
				for morph in src_token.split('-'):
					if stem:
						morph = stem_token(morph)
					
					# Take the index that is in line with this one...
					tgt_indices = all_indices(morph, tgt_tokens)
					for tgt_i in tgt_indices:
						existing_pair = alignments.contains_tgt(tgt_i)
						
						
						# Otherwise, assign left-to-right
						alignments.add((src_i+1, tgt_i+1))
						break
					
	elif aln_direction == 'b':
		for tgt_i in range(len(tgt_tokens)):
			tgt_token = tgt_tokens[tgt_i]
			
			if tgt_token in src_tokens:
				src_i = src_tokens.index(tgt_token)
				alignments.add((src_i+1, tgt_i+1))
				
			if morph_on:
				for morph in tgt_token.split('-'):
					if stem:
						morph = stem_token(morph)
					
					# Take the index that is in line with this one...
					src_indices = all_indices(morph, src_tokens)
					for src_i in src_indices:
						existing_pair = alignments.contains_tgt(tgt_i)
						
						# If the target token has already been assigned, skip it
# 						if alignments.contains_src(src_i):
# 							continue
						
						# Otherwise, assign left-to-right
						alignments.add((src_i+1, tgt_i+1))
						break
			
		
	
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