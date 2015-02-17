#!/usr/bin/env python

'''
Created on Apr 30, 2014

@author: rgeorgi
'''
from corpora.IGTCorpus import IGTCorpus, IGTProjectionException,\
	IGTGlossLangLengthException, IGTAlignmentException
from interfaces.mallet_maxent import MalletMaxent
import pickle
from argparse import ArgumentParser
from utils.argutils import existsfile
from utils.ConfigFile import ConfigFile
from interfaces.stanford_tagger import StanfordPOSTagger

import logging
import os
import sys

projection_logger = logging.getLogger('projection')
classification_logger = logging.getLogger('classification')


if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--conf', required=True, type=existsfile)
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	# Build the corpus...
	corp = IGTCorpus.from_text(c.get('txt_path', t=existsfile),
					merge=True, mode='full')

	posdict = pickle.load(open(c.get('posdict', t=existsfile), 'rb'))

	# Get the output path for the slashtags...
	outpath = c.get('out_path')
	os.makedirs(os.path.dirname(outpath), exist_ok=True)

	# The output in slashtags format...
	tagger_out = open(outpath, 'w', encoding='utf-8')

	if c.get('tagging_method') == 'projection':
		spt = StanfordPOSTagger(c.get('eng_tagger'))
	else:
		# Load the classifier...
		classifier = MalletMaxent(c.get('classifier', t=existsfile))
		

	i = 0
	skipped = 0

	for inst in corp:
		
		if i % 10 == 0:
			print('Processing instance %d...' % i)
		
		i+=1
		sequence = []
		
		
		
		#=======================================================================
		# Try the projection method for labeling the corpus if specified...
		#======================================================================
		if c.get('tagging_method') == 'projection':
		
			try:
				sequence = inst.lang_line_projections(spt, posdict=posdict, lowercase=True, error_on_nonproject=c.get('skip_proj_errors', t=bool))
			except IGTProjectionException as igtpe:
				projection_logger.warning('There was an error in projection: %s' % igtpe)
				skipped += 1
				continue
			except IGTGlossLangLengthException as e:
				skipped +=1
				continue
			except IGTAlignmentException as iae:
				skipped +=1
				continue
				
		
		#=======================================================================
		# Otherwise, use the classification approach.
		#=======================================================================
		else:
			try:
				sequence = inst.lang_line_classifications(classifier, posdict=posdict, 
													feat_dict=True,
													feat_next_gram=True,
													feat_prev_gram=True,
													feat_prefix=True,
													feat_suffix=True,
													lowercase=True)
			except IGTGlossLangLengthException as e:
				#classification_logger.warning('Gloss and language lines did not match up for: %s' % inst.text())
				skipped += 1
				continue
				
	
		
		if sequence:
			for token in sequence:
				tagger_out.write('%s/%s ' % (token.seq, token.label))
			
			tagger_out.write('\n')
			
	print('%d skipped ' % skipped)
		
	tagger_out.close()