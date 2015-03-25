'''
Created on Mar 24, 2015

@author: rgeorgi
'''

import intent.igt.rgxigt as rgx
from intent.utils.env import c
from intent.utils.argutils import writefile
from intent.interfaces.stanford_tagger import StanfordPOSTagger, TaggerError
import sys, logging

# XIGT imports -----------------------------------------------------------------
from xigt.codecs import xigtxml
import intent.interfaces.giza
from intent.interfaces.giza import GizaAlignmentException

#===============================================================================
# The ENRICH subcommand.
#===============================================================================

def enrich(**kwargs):
	inpath = kwargs.get('IN_FILE')
	print('Loading input file...')
	corp = rgx.RGCorpus.load(inpath)
	
	#===========================================================================
	# If the tagger is asked for, initialize it.
	#===========================================================================
	if kwargs.get('pos_trans'):
		print('Initializing tagger...')
		tagger = c.getpath('stanford_tagger_trans')
	
		try:
			s = StanfordPOSTagger(tagger)
		except TaggerError:
			sys.exit(2)
	
	#===========================================================================
	# If alignment is requested, add it.
	#===========================================================================
	if kwargs.get('alignment') == 'heur':
		print('Heuristically aligning instances...')
		corp.heur_align()
	elif kwargs.get('alignment') == 'giza':
		print('Aligning instances using GIZA++...')
		try:
			corp.giza_align_t_g()
		except GizaAlignmentException as gae:
			gl = logging.getLogger('giza')
			gl.critical(str(gae))
			sys.exit(2)
			
		
	
	for inst in corp:
		if kwargs.get('pos_trans'):
			inst.tag_trans_pos(s)

	print('Writing output file...', end=' ')	
	xigtxml.dump(writefile(kwargs.get('OUT_FILE')), corp)
	print('Done.')