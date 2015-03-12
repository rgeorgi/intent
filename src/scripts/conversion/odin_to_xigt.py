#!/usr/bin/env python

'''
Created on Apr 30, 2014

@author: rgeorgi
'''

import pickle
from argparse import ArgumentParser
from utils.argutils import existsfile
from utils.ConfigFile import ConfigFile


from utils.setup_env import c as e

import logging
import os
import sys
from igt.rgxigt import RGCorpus, rgp, NoTransLineException
from glob import glob
from xigt.codecs import xigtxml

PARSELOGGER = logging.getLogger(__name__)


def parse_text(txt_path, xigt_path):

	# 1) Build the corpus --------------------------------------------------
	
	corp = RGCorpus.from_txt(txt_path, require_trans=False, require_gloss=True, require_lang=True, require_1_to_1=True)
	
	# 2) load the pos dict to help classify the gloss line ---------------------
	posdict = pickle.load(open(e.get('pos_dict', t=existsfile), 'rb'))

	# 4) Initialize tagger/classifier ---
	
	spt = StanfordPOSTagger(e.get('stanford_tagger_trans'))
	classifier = MalletMaxent(e.get('classifier_model', t=existsfile))
	
	#===========================================================================
	# Tag the translation line and gloss lines. We can replace this later
	# with projection.
	#===========================================================================
		
	i = 0
	for inst in corp:
		
		if i % 10 == 0:
			print('Processing instance %d...' % i)
		
		i+=1
		
		# Only tag the trans line if it has it
		try:
			inst.tag_trans_pos(spt)
		except NoTransLineException as ntle:
			logging.warn(ntle)
			
		inst.classify_gloss_pos(classifier,
									posdict=posdict,
									feat_dict=True,
									feat_prev_gram=True,
									feat_prefix=True,
									feat_suffix=True,
									lowercase=True)
		
	# TODO FIXME: How to gracefully handle generating a corpus that doesn't require a translation line
	corp.heur_align()

		
	xigt_f = open(xigt_path, 'w', encoding='utf-8')
	xigtxml.dump(xigt_f, corp)
	xigt_f.close()
		
from interfaces.stanford_tagger import StanfordPOSTagger
from interfaces.mallet_maxent import MalletMaxent

if __name__ == '__main__':
	
	p = ArgumentParser()
	p.add_argument('-i', '--input', required=True, help='Input text file to convert to annotated xigt.')
	p.add_argument('-o', '--output', required=True, help='Output xigt path.')
	
	args = p.parse_args()
	
	
	parse_text(args.input, args.output)