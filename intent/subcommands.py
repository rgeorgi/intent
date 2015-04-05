'''
Created on Mar 24, 2015

@author: rgeorgi
'''

import sys, logging, pickle

from intent.igt.rgxigt import RGCorpus, GlossLangAlignException,\
	PhraseStructureProjectionException, ProjectionException,\
	ProjectionTransGlossException, rgp, word_align
from intent.utils.env import c, classifier, posdict
from intent.utils.argutils import writefile
from intent.interfaces.stanford_tagger import StanfordPOSTagger, TaggerError, CriticalTaggerError

from intent.interfaces.giza import GizaAlignmentException
from intent.interfaces import mallet_maxent, stanford_parser

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
	# Initialize the parser 
	#===========================================================================
	if kwargs.get('parse_trans'):
		print("Intializing English parser...")
		sp = stanford_parser.StanfordParser()
			
	#===========================================================================
	# If the classifier is asked for, initialize it...
	#===========================================================================
	if kwargs.get('pos_lang') == 'class':
		print("Initializing gloss-line classifier...")
		p = posdict
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
		
		# Attempt to align the gloss and language lines if requested... --------
		word_align(inst.gloss, inst.lang)
		
		# 3) POS tag the translation line --------------------------------------
		if kwargs.get('pos_trans'):
			try:
				inst.tag_trans_pos(s)
			except CriticalTaggerError as cte:
				ENRICH_LOG.critical(str(cte))
				sys.exit(2)
			
		# 4) POS tag the gloss line --------------------------------------------
		if kwargs.get('pos_lang') == 'class':
			inst.classify_gloss_pos(m, posdict=p)
			try:
				inst.project_gloss_to_lang(created_by="intent-classify")
			except GlossLangAlignException:
				ENRICH_LOG.warning('The gloss and language lines for instance id "%s" do not align. Language line not POS tagged.' % inst.id)
				
		elif kwargs.get('pos_lang') == 'proj':
			try:
				inst.project_trans_to_gloss()
			except ProjectionTransGlossException as ptge:
				ENRICH_LOG.warning('No alignment between translation and gloss lines found for instance "%s". Not projecting POS tags.' % inst.id)
			except ProjectionException as pe:
				ENRICH_LOG.warning('No translation POS tags were found for instance "%s". Not projecting POS tags.' % inst.id)
			else:
				inst.project_gloss_to_lang()
				
			
				
		# 5) Parse the translation line ----------------------------------------
		if kwargs.get('parse_trans'):
			inst.parse_translation_line(sp, pt=True, dt=True)
			
		# If parse tree projection is enabled... -------------------------------
		if kwargs.get('project_pt'):
			try:
				inst.project_pt()
			except PhraseStructureProjectionException as pspe:
				ENRICH_LOG.warning('A parse for the translation line was not found for instance "%s", not projecting phrase structure.' % inst.id)
			except ProjectionTransGlossException as ptge:
				ENRICH_LOG.warning('Alignment between translation and gloss lines was not found for instance "%s". Not projecting phrase structure.' % inst.id)
				
		# Sort the tiers... ----------------------------------------------------
		inst.sort()

	print('Writing output file...', end=' ')	
	xigtxml.dump(writefile(kwargs.get('OUT_FILE')), corp)
	print('Done.')