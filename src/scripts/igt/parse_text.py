#!/usr/bin/env python

'''
Created on Apr 30, 2014

@author: rgeorgi
'''
from interfaces.mallet_maxent import MalletMaxent
import pickle
from argparse import ArgumentParser
from utils.argutils import existsfile
from utils.ConfigFile import ConfigFile
from interfaces.stanford_tagger import StanfordPOSTagger

import logging
import os
import sys
from igt.rgxigt import RGCorpus, rgp

projection_logger = logging.getLogger('projection')
classification_logger = logging.getLogger('classification')

def parse_text(c):

	# 1) Build the corpus --------------------------------------------------
	#corp = pickle.load(open('corp.pkl', 'rb'))
	# If we are using classification, we do not require a translation line...
	require_trans = True
	if c.get('tagging_method') == 'classification':
		require_trans = False
	
	corp = RGCorpus.from_txt(c.get('txt_path', t=existsfile), require_trans = require_trans)

	# 2) load the pos dict to help classify the gloss line ---------------------
	posdict = pickle.load(open(c.get('posdict', t=existsfile), 'rb'))

	# 3) Get the output path for the slashtags... -------------------------------
	outpath = c.get('out_path')
	os.makedirs(os.path.dirname(outpath), exist_ok=True)

	tagger_out = open(outpath, 'w', encoding='utf-8')

	# 4) Initialize tagger/classifier ---
	if c.get('tagging_method') == 'projection':
		spt = StanfordPOSTagger(c.get('eng_tagger'))
	else:
		# Load the classifier...
		classifier = MalletMaxent(c.get('classifier', t=existsfile))
		

	i = 0
	skipped = 0
	
	#===========================================================================
	# 5) Align the corpus for projection ---
	#===========================================================================
	if c.get('tagging_method') == 'projection':
		# If the alignment method is giza, use giza to align the
		# gloss and translation.
		if c.get('alignment_method', 'heur') == 'giza':
			corp.giza_align_g_t()

		# Otherwise, perform heuristic alignment.		
		else:
			corp.heur_align()

		
	#=======================================================================
	# 6) Iterate over the instances in the corpus ---
	#=======================================================================
	for inst in corp:
		
		if i % 10 == 0:
			print('Processing instance %d...' % i)
		
		i+=1
		sequence = []
		
		
		
		#=======================================================================
		# a) Try the projection method for labeling the corpus if specified... ---
		#======================================================================
		if c.get('tagging_method') == 'projection':
			
			inst.tag_trans_pos(spt)
			inst.project_trans_to_gloss()
			inst.project_gloss_to_lang()
			
		
		#=======================================================================
		# b) Otherwise, use the classification approach. ---
		#=======================================================================
		else:
			inst.classify_gloss_pos(classifier,
									posdict=posdict,
									feat_dict=True,
									feat_prev_gram=True,
									feat_prefix=True,
									feat_suffix=True,
									lowercase=True)
			inst.project_gloss_to_lang()
			
		
		sequence = inst.get_lang_sequence()
		
		if c.get('skip_proj_errors') and len(sequence) != len([i for i in sequence if i.label != 'UNK']):
			skipped += 1
			continue 
				
	
		
		if sequence:
			for token in sequence:
				tagger_out.write('%s/%s ' % (token.seq, token.label))
			
			tagger_out.write('\n')
			
	print('%d skipped ' % skipped)
		
	tagger_out.close()


if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--conf', required=True, type=existsfile)
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	parse_text(c)
	