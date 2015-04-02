'''
Created on Feb 26, 2015

@author: rgeorgi
'''
import intent.utils
from . rgxigt import RGWordTier, RGWord, RGPhraseTier, RGPhrase, GlossLangAlignException, RGMorph
from collections import defaultdict
from xigt.core import get_alignment_expression_ids, ALIGNMENT, algnexpr_re,\
	get_alignment_expression_spans, resolve_alignment_expression, CONTENT
from intent.igt.rgxigt import ODIN_GLOSS_TAG, GLOSS_WORD_TYPE, GLOSS_MORPH_TYPE,\
	rgp, GLOSS_WORD_ID, TRANS_WORD_TYPE, TRANS_PHRASE_TYPE, ODIN_TRANS_TAG,\
	TRANS_PHRASE_ID, LANG_PHRASE_ID, LANG_PHRASE_TYPE, ODIN_LANG_TAG,\
	LANG_WORD_TYPE, LANG_WORD_ID, TRANS_WORD_ID, LANG_MORPH_TYPE, PS_TIER_TYPE,\
	ALN_TIER_TYPE, DS_TIER_TYPE, POS_TIER_TYPE, ODIN_TYPE, NORM_STATE, CLEAN_STATE,\
	RAW_STATE
import sys
import re
from intent.utils.token import tokenize_item


#===============================================================================
# • Basic Functions
#===============================================================================
def create_aln_expr(id, start=None, stop=None):
	'''
	Create an alignment expression, such as ``n2[5:8]`` or ``tw1`` given an id, and start/stop range.
	
	:param id: ID with which to align
	:type id: str
	:param start: Range at which to start
	:type start: int
	:param stop: Range at which to stop
	:type stop: int
	'''
	
	if start is None and stop is None:
		return id
	elif start is not None and stop is not None:
		return '%s[%d:%d]' % (id, start, stop)
	else:
		raise Exception('Invalid alignment expression request')

#===============================================================================
# • Tier Creation ---
#===============================================================================

def create_words_tier(cur_item, word_id, word_type):
	'''
	Create a words tier from an ODIN line type item.
	
	:param cur_item: Either a phrase item or a line item to tokenize and create words form.
	:type cur_item: RGItem
	:param word_id: The ID for this tier.
	:type word_id: str
	:param word_type: Tier type for this tier.
	:type word_type: str
	'''
	
	# Tokenize the words in this phrase...
	words = intent.utils.token.tokenize_item(cur_item)
	
	# Create a new word tier to hold the tokenized words...
	wt = RGWordTier(id = word_id, type=word_type, content=cur_item.tier.id, igt=cur_item.igt)
	
	for w in words:
		# Create a new word that is a segmentation of this tier.
		rw = RGWord(id=wt.askItemId(), content=create_aln_expr(cur_item.id, w.start, w.stop), tier=wt)
		wt.add(rw)
	
	return wt



def retrieve_gloss(inst):
	'''
	Given an IGT instance, create the gloss "words" and "glosses" tiers.
	
	1. If a "words" type exists, and it's contents are the gloss line, return it.
	2. If it does not exist, tokenize the gloss line and return it.
		
	:param inst: Instance which to create the tiers from.
	:type inst: RGIgt
	'''
	
	# 1. Look for an existing words tier that aligns with the normalized tier...
	n = inst.normal_tier()
	wt = inst.find(type=GLOSS_WORD_TYPE, content = n.id)
	
	# 2. If it exists, return it. Otherwise, look for the glosses tier.
	if not wt:
		wt = create_words_tier(retrieve_normal_line(inst, ODIN_GLOSS_TAG), GLOSS_WORD_ID, GLOSS_WORD_TYPE)
		inst.add(wt)
	else:
		wt.__class__ = RGWordTier
		
	return wt

def retrieve_trans_phrase(inst):
	tpt = retrieve_phrase(inst, ODIN_TRANS_TAG, TRANS_PHRASE_ID, TRANS_PHRASE_TYPE)
	
	# Add the alignment with the language line phrase if it's not already there.
	if ALIGNMENT not in tpt.attributes:
		lpt = retrieve_lang_phrase(inst)
		tpt.attributes[ALIGNMENT] = lpt.id
		tpt[0].attributes[ALIGNMENT] = lpt[0].id
		
	return tpt

def retrieve_lang_phrase(inst):
	return retrieve_phrase(inst, ODIN_LANG_TAG, LANG_PHRASE_ID, LANG_PHRASE_TYPE)

def retrieve_phrase(inst, tag, id, type):
	'''
	Retrieve a phrase for the given tag, with the provided id and type.
	
	:param inst: Instance to retrieve the elements from.
	:type inst: RGIgt
	:param tag: 'L', 'G' or 'T'
	:type tag: str
	:param id: 
	:type id: str
	:param type: 
	:type type: str
	'''
	
	n = inst.normal_tier()
	
	pt = inst.find(type=type, content = n.id)
	if not pt:
		# Get the normalized line line
		l = retrieve_normal_line(inst, tag)
		pt = RGPhraseTier(id=id, type=type, content=n.id)
		pt.add(RGPhrase(id=pt.askItemId(), content=l.id))
		inst.add(pt)
	else:
		pt.__class__ = RGPhraseTier
		
	return pt

def retrieve_trans_words(inst):

	# Get the translation phrase tier
	tpt = retrieve_trans_phrase(inst)
	
	# Get the translation word tier
	twt = inst.find(type=TRANS_WORD_TYPE, content=tpt.id)

	if not twt:
		twt = create_words_tier(tpt[0], TRANS_WORD_ID, TRANS_WORD_TYPE)
		inst.add(twt)
	else:
		twt.__class__ = RGWordTier
	
	return twt
	
def retrieve_lang_words(inst):
	# Get the lang phrase tier
	lpt = retrieve_lang_phrase(inst)
	
	# Get the lang word tier
	lwt = inst.find(type=LANG_WORD_TYPE, content=lpt.id)
	
	if not lwt:
		lwt = create_words_tier(lpt[0], LANG_WORD_ID, LANG_WORD_TYPE)
		inst.add(lwt)
	else:
		lwt.__class__ = RGWordTier
		
	return lwt
	

def retrieve_normal_line(inst, tag):
	'''
	Retrieve a normalized line from the instance ``inst`` with the given ``tag``.
	
	:param inst: Instance to retrieve the normalized line from.
	:type inst: RGIgt
	:param tag: {'L', 'G', or 'T'}
	:type tag: str
	'''
	
	n = inst.normal_tier()
	
	lines = [l for l in n if tag in l.attributes['tag'].split('+')]
	
	assert len(lines) == 1, "There should not be more than one line for each tag in the normalized tier."
	
	return lines[0]

		
	
#===============================================================================
# Alignment Utilities ---
#===============================================================================

def word_align(this, other):
	
	if len(this) != len(other):
		raise GlossLangAlignException('Gloss and language lines could not be auto-aligned for igt "%s"' % this.igt.id)
	else:
		# Note on the tier the alignment
		this.alignment = other.id
		
		# Align the words 1-to-1, left-to-right
		for my_word, their_word in zip(this, other):
			my_word.alignment = their_word.id
			
def morph_align(this, other):
	# Let's count up how many morphemes there are
	# for each word on the translation line...
	
	
	lang_word_dict = defaultdict(list)
	for other_m in other:
		other_m.__class__ = RGMorph
		
		# Add this morpheme to the dictionary, so we can keep
		# count of how many morphemes align to a given word.
		lang_word_dict[other_m.word.id].append(other_m)

		
	# Now, iterate over our morphs.
	for this_m in this:
		
		
		this_m.__class__ = RGMorph
		
		# Find our parent word, and it's
		# alignment.

		w = this_m.word
		other_w_id = w.alignment
		
		# Next, let's see what unaligned morphs there are
		other_w_list = lang_word_dict[other_w_id]
		
		# If there's only one morph left, align with that.
		if len(other_w_list) == 1:
			this_m.alignment = other_w_list[0].id
			
		# If there's more, pop one off the beginning of the list and use that.
		elif len(other_w_list) > 1:
			this_m = other_w_list.pop(0)
			this_m.alignment = this_m.id	
			
#===============================================================================
# • Searching ---
#===============================================================================

def word(morph):
	
	if morph.content:
		id = get_alignment_expression_ids(morph.content)[0]
		
		# TODO: Finding a "Word" here requires a words tier, which may or may not exist already.
		word = morph.tier.igt.find(id=id)	
		word.__class__ = RGWord
		return word
	else:
		return None

def follow_alignment(inst, id):
	'''
	If the given ID is aligned to another item, return that other item. If that item
	is aligned to another item, return THAT item's ID, and so on.
	'''
	
	# Return none if this id isn't found.
	found = inst.find(id)
	w = word(found) if found else None
	
	if not found:
		return None
	
	# Look to see if there's an alignment attribute.
	if found.alignment:
		return follow_alignment(inst, found.alignment)
	
	# If there's not a word that this is a part of, 	
	if w:
		return follow_alignment(inst, w.id)
	
	else:		
		return found


#===============================================================================
# • Sorting ---
#===============================================================================

def sort_idx(l, v):
	'''
	Return the index of an item in a list, otherwise the length of the list (for sorting)
	
	:param l: list
	:param v: value
	'''
	try:
		return l.index(v)
	except:
		return len(l)

def tier_sorter(x):
	'''
	``key=`` function to sort a tier according to tier type,
	tier state (for ODIN tiers), and word_id (for word
	tiers that all share the same type attribute)
	'''
	type_order = [ODIN_TYPE, 
					LANG_PHRASE_TYPE, TRANS_PHRASE_TYPE,
					LANG_WORD_TYPE, GLOSS_WORD_TYPE, TRANS_WORD_TYPE,
					LANG_MORPH_TYPE, GLOSS_MORPH_TYPE,
					POS_TIER_TYPE, ALN_TIER_TYPE, PS_TIER_TYPE, DS_TIER_TYPE, None]
	
	state_order = [RAW_STATE, CLEAN_STATE, NORM_STATE]	
	word_id_order = [LANG_WORD_ID, GLOSS_WORD_ID, TRANS_WORD_ID]
	
	
	state_index = sort_idx(state_order, x.attributes.get('state'))
	type_index = sort_idx(type_order, x.type)
	id_index = sort_idx(word_id_order, x.id)
	
	return (type_index, state_index, id_index, x.id)
	
#===============================================================================
# • Cleaning ---
#===============================================================================


def strip_enrichment(inst):
	strip_pos(inst)
	for at in inst.findall(type='bilingual-alignments'):
		at.delete()
	
def strip_pos(inst):
	for pt in inst.findall(type='pos'):
		pt.delete()
	