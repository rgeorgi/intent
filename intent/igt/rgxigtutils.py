'''
Created on Feb 26, 2015

@author: rgeorgi
'''
import intent.utils
from .rgxigt import RGWordTier, RGWord, RGPhraseTier, RGPhrase, GlossLangAlignException, RGMorph
from collections import defaultdict
from xigt.core import get_alignment_expression_ids


#===============================================================================
# • Tier Creation ---
#===============================================================================

def create_words_tier(cur_item, word_id, word_type):
	
	# Tokenize the words in this phrase...
	words = intent.utils.token.tokenize_item(cur_item)
	
	# Create a new word tier to hold the tokenized words...
	wt = RGWordTier(id = word_id, type=word_type, segmentation=cur_item.tier.id, igt=cur_item.igt)
	
	for w in words:
		# Create a new word that is a segmentation of this tier.
		rw = RGWord(id=wt.askItemId(), segmentation='%s[%s:%s]' % (cur_item.id, w.start, w.stop), tier=wt)
		wt.add(rw)
	
	return wt


def create_phrase_tier(cur_item, phrase_id, phrase_type):
	'''
	Create a phrase tier from a current normalized line.
	
	:param cur_item:
	:type cur_item:
	:param phrase_id:
	:type phrase_id:
	:param phrase_type:
	:type phrase_type:
	'''
	
	pt = RGPhraseTier(id=phrase_id, type=phrase_type, content=cur_item.tier.id, igt=cur_item.igt)
	pt.add(RGPhrase(id=pt.askItemId(), content=cur_item.id, tier=pt))
	return pt
	
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
# • Cleaning ---
#===============================================================================

def strip_enrichment(inst):
	strip_pos(inst)
	for at in inst.findall(type='bilingual-alignments'):
		at.delete()
	
def strip_pos(inst):
	for pt in inst.findall(type='pos'):
		pt.delete()
	