'''
Created on Mar 24, 2015

@author: rgeorgi
'''

import intent.igt.rgxigt as rgx
from intent.utils.setup_env import c
from intent.utils.argutils import writefile
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from xigt.codecs import xigtxml

# XIGT imports -----------------------------------------------------------------

#===============================================================================
# The ENRICH subcommand.
#===============================================================================

def enrich(**kwargs):
	inpath = kwargs.get('IN_FILE')
	corp = rgx.RGCorpus.load(inpath)
	
	# Get the tagger.
	tagger = c.getpath('stanford_tagger_trans')
	s = StanfordPOSTagger(tagger)
	
	for inst in corp:
		if kwargs.get('pos_trans'):
			inst.tag_trans_pos(s)
	
	xigtxml.dump(writefile(kwargs.get('OUT_FILE')), corp)