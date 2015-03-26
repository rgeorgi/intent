'''
Created on Mar 24, 2015

@author: rgeorgi
'''

import sys, logging, pickle

from intent.igt.rgxigt import RGCorpus, GlossLangAlignException
from intent.utils.env import c, classifier, posdict
from intent.utils.argutils import writefile
from intent.interfaces.stanford_tagger import StanfordPOSTagger, TaggerError
import intent.interfaces.giza
from intent.interfaces.giza import GizaAlignmentException
from intent.interfaces import mallet_maxent

# XIGT imports -----------------------------------------------------------------
from xigt.codecs import xigtxml


#===============================================================================
# The ENRICH subcommand.
#===============================================================================

def enrich(**kwargs):
	
	ENRICH_LOG = logging.getLogger('ENRICH')
	
	inpath = kwargs.get('IN_FILE')
	print('Loading input file...')
	corp = RGCorpus.load(inpath)
	
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
	# If the classifier is asked for, initialize it...
	#===========================================================================
	if kwargs.get('pos_lang') == 'class':
		print("Initializing gloss-line classifier...")
		p = pickle.load(open(posdict, 'rb'))
		m = mallet_maxent.MalletMaxent(classifier)
	
	# -- 1a) Heuristic Alignment --------------------------------------------------
	if kwargs.get('alignment') == 'heur':
		print('Heuristically aligning gloss and translation lines...')
		corp.heur_align()
		
	# -- 1b) Giza Gloss to Translation alignment --------------------------------------
	elif kwargs.get('alignment') == 'giza':
		print('Aligning gloss and translation lines using mgiza++...')
		
		try:
			corp.giza_align_t_g()
		except GizaAlignmentException as gae:
			gl = logging.getLogger('giza')
			gl.critical(str(gae))
			sys.exit(2)
			
	# -- 2) Iterate through the corpus -----------------------------------------------
	for inst in corp:
		
		# 3) POS tag the translation line --------------------------------------
		if kwargs.get('pos_trans'):
			inst.tag_trans_pos(s)
			
		if kwargs.get('pos_lang') == 'class':
			inst.classify_gloss_pos(m, posdict=p)
			try:
				inst.project_gloss_to_lang(created_by="intent-classify")
			except GlossLangAlignException:
				ENRICH_LOG.warning('The gloss and language lines for instance id "%s" do not align. Language line not POS tagged.' % inst.id)

	print('Writing output file...', end=' ')	
	xigtxml.dump(writefile(kwargs.get('OUT_FILE')), corp)
	print('Done.')