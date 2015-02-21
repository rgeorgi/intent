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

from utils.setup_env import c as e

import logging
import os
import sys
from igt.rgxigt import RGCorpus, rgp, NoTransLineException
from glob import glob
from xigt.codecs import xigtxml

projection_logger = logging.getLogger('projection')
classification_logger = logging.getLogger('classification')

def parse_text(txt_path, xigt_path):

	# 1) Build the corpus --------------------------------------------------
	
	corp = RGCorpus.from_txt(txt_path, require_trans=False)
	
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
		
	
	corp.heur_align()
		
	xigt_f = open(xigt_path, 'w', encoding='utf-8')
	xigtxml.dump(xigt_f, corp)
	xigt_f.close()
	sys.exit()
	
# 	i = 0
# 	skipped = 0
# 	
# 	#===========================================================================
# 	# 5) Align the corpus for projection ---
# 	#===========================================================================
# 	if c.get('tagging_method') != 'classification':
# 		# If the alignment method is giza, use giza to align the
# 		# gloss and translation.
# 		if c.get('alignment_method') == 'giza':
# 			corp.giza_align_t_g()
# 			
# 		elif c.get('alignment_method') == 'giza-direct':
# 			corp.giza_align_l_t()
# 		# Otherwise, perform heuristic alignment.		
# 		else:
# 			corp.heur_align()
# 
# 		
# 	#=======================================================================
# 	# 6) Iterate over the instances in the corpus ---
# 	#=======================================================================
# 	for inst in corp:
# 		
# 		if i % 10 == 0:
# 			print('Processing instance %d...' % i)
# 		
# 		i+=1
# 		sequence = []
# 		
# 		print(c.get('tagging_method'))
# 		
# 		#=======================================================================
# 		# a) Try the projection method for labeling the corpus if specified... ---
# 		#======================================================================
# 		if c.get('tagging_method') == 'projection':
# 			
# 			inst.tag_trans_pos(spt)
# 			inst.project_trans_to_gloss()
# 			inst.project_gloss_to_lang()
# 			
# 		elif c.get('tagging_method') == 'direct-projection':
# 			inst.tag_trans_pos(spt)
# 			inst.project_trans_to_lang()
# 			
# 		
# 		#=======================================================================
# 		# b) Otherwise, use the classification approach. ---
# 		#=======================================================================
# 		else:
# 			inst.classify_gloss_pos(classifier,
# 									posdict=posdict,
# 									feat_dict=True,
# 									feat_prev_gram=True,
# 									feat_prefix=True,
# 									feat_suffix=True,
# 									lowercase=True)
# 			inst.project_gloss_to_lang()
# 			
# 		
# 		sequence = inst.get_lang_sequence()
# 		
# 		if c.get('skip_proj_errors') and len(sequence) != len([i for i in sequence if i.label != 'UNK']):
# 			skipped += 1
# 			continue 
# 				
# 	
# 		
# 		if sequence:
# 			for token in sequence:
# 				tagger_out.write('%s/%s ' % (token.seq, token.label))
# 			
# 			tagger_out.write('\n')
# 			
# 	print('%d skipped ' % skipped)
# 		
# 	tagger_out.close()


if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-i', '--input', required=True, help='Input text file to convert to annotated xigt.')
	p.add_argument('-o', '--output', required=True, help='Output xigt path.')
	
	args = p.parse_args()
	
	parse_text(args.input, args.output)