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
from utils.string_utils import stem_token



def morphfilter(m):
	for elt in m:
		if elt.lower() in ['acc', 'dat', 'inf']:
			m = m - set([elt])
	return m

	

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