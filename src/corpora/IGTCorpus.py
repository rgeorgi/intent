'''
Created on Mar 7, 2014

@author: rgeorgi
'''
from alignment.Alignment import Alignment, AlignedSent
import re
from unidecode import unidecode
import sys

import unittest
from utils.string_utils import stem_token, lemmatize_token
from igt.grams import sub_grams

class IGTCorpus(list):
	'''
	Object that will hold a corpus of IGT instances.
	'''

	def __init__(self, seq = []):
		list.__init__(self, seq)

	def gloss_alignments(self):
		return [inst.get_gloss_align_sent() for inst in self]

	def lang_alignments(self):
		return [inst.get_lang_align_sent() for inst in self]
	
	def gloss_heuristic_alignments(self, lowercase=True, stem=True, tokenize=True):
		return [inst.gloss_heuristic_alignment(lowercase=lowercase, stem=stem, morph_on=tokenize) for inst in self]
		
		
class IGTInstance(list):
	'''
	Container class for an IGT instance and all the dealings that will go on inside it.
	'''
	
	def __init__(self, seq=[], id = None):
		self._id = id
		self.glossalign = Alignment()
		self.langalign = Alignment()
		list.__init__(self, seq)
		self.attrs = {}
		
	def get_gloss_align_sent(self):
		# TODO: Again with the zero-indexing...
		a = AlignedSent(self.gloss()[0], self.trans()[0], self.glossalign)
		a.attrs = self.attrs
		return a
	
	def get_lang_align_sent(self):
		# TODO: Guess what...
		a = AlignedSent(self.gloss()[0], self.trans()[0], self.langalign)
		a.attrs = self.attrs
		return a
		
	def append(self, item):
		if not isinstance(item, IGTTier):
			raise IGTException('Attempt to append a non-IGTTier instance to an IGTInstance')
		list.append(self, item)
		
	def gloss(self):
		return [tier for tier in self if tier.kind == 'gloss']
	
	def trans(self):
		return [tier for tier in self if tier.kind == 'trans']
	
	def lang(self):
		return [tier for tier in self if tier.kind == 'lang']
	
	def set_attr(self, key, val):
		self.attrs[key] = val
		
	def get_attr(self, key):
		return self.attrs[key]
	

	
	def __str__(self):
		ret_str = ''
		for kind in set([tier.kind for tier in self]):
			ret_str += '%s,'%str(kind)
		return '<IGTInstance %d: %s>' % (self._id, ret_str[:-1])
	
	def gloss_heuristic_alignment(self, **kwargs):
		
		# FIXME: Make sure that when there are multiple occurrences of a token, they are aligned left-to-right.
		
		# TODO: Again, we're working with zero-indices here... not liking it.
		gloss = self.gloss()[0]
		trans = self.trans()[0]
		
		aln = Alignment()
		
		for gloss_i in range(len(gloss)):
			gloss_token = gloss[gloss_i]
						
			#===================================================================
			# Before we even take a look at the morphs, just look at the
			# token on its own.
			#===================================================================
						
			# TODO: Find a way to match left-to-right just once, and not repeat it for each time.
			#       perhaps only start from the current instance?
			
			matches = match_multiples(gloss_token, gloss, trans, **kwargs)
			for a, b in matches:
				aln.add((a+1,b+1))
				
		
		#=======================================================================
		#  Second pass...
		#
		# After we've taken a single pass and seen what we could do, let's take a second
		# pass on the remaining unaligned bits, and see if we can't pick up a few stragglers
		# with info like grams.
		#=======================================================================
		for gloss_i in range(len(gloss)):
			gloss_token = gloss[gloss_i]
			
			# Skip over any previously-aligned tokens
			if not aln.contains_src(gloss_i+1):
				
				kwargs['gloss_on'] = True				
				matches = match_multiples(gloss_token, gloss, trans, **kwargs)
				for a, b in matches:
					aln.add((a+1,b+1))
						
		a = AlignedSent(gloss, trans, aln)
		a.attrs = self.attrs
		return a
		
def alltrue(sequence, comparator = lambda x, y: x == y):
	'''
	Do an all-ways comparison to make sure everything in the list returns true from the comparator value.
	
	@param sequence:
	@param comparator:
	@param y:
	'''
	ret = True
	for i in range(len(sequence)):
		item = sequence[i]
		for rest in sequence[:i]+sequence[i+1:]:
			if not comparator(item, rest):
				ret = False
	return ret

def match_multiples(item, src_sequence, tgt_sequence, **kwargs):
	'''
	Code to take an item with source and target sequences, and match
	them left to right as necessary.
	
	If there are multiple words that match in both the source and target,
	we would like to match them from left to right in order.
	
	@param item:
	@param src_sequence:
	@param tgt_sequence:
	'''
	
	# TODO: Think more about how I should handle multiple left-to-right alignments
	#       right now, these are, well, not handled, the search is re-done each time
	#       a token is encountered. Perhaps instead I should do something like mark
	#       the visisted tokens, or pop them or something...
	
	src_indices = src_sequence.search(item, **kwargs)
	tgt_indices = tgt_sequence.search(item, **kwargs)
	
	#===========================================================================
	#  Filter out the matched source items in advance to make sure that they
	#  actually match one of the target items and not just some other portion
	#  of the source item.
	#===========================================================================
	
	filtered_src_indices = []	
	
	for src_index in src_indices:
		src_item = src_sequence[src_index]
		for tgt_index in tgt_indices:
			tgt_item = tgt_sequence[tgt_index]
			if src_item.morphequals(tgt_item, **kwargs):
				if src_index not in filtered_src_indices:
					filtered_src_indices.append(src_index)
				
	src_indices = filtered_src_indices
	
	#  -----------------------------------------------------------------------------
	
	if src_indices and tgt_indices:
		
		# Start by popping the leftmost indices
		src_index = src_indices.pop(0)		
		tgt_index = tgt_indices.pop(0)
		
		# Loop until we break out
		while True:
								
			# Make sure 
			if src_sequence[src_index].morphequals(tgt_sequence[tgt_index], **kwargs):			
				yield((src_index, tgt_index))
			else:
				if len(src_indices) >= 1:
					src_index = src_indices.pop()
					continue
				else:
					break
			
			# FIXME: So, the bug here is in the case where we have multiple matches in the source line,
			#        but they do not correspond to multiple matches in the target line.
			#        I'm thinking what I need to do is filter out the source line for things that
			#        match the source word, yes, but that also match the target word in question. 
			# 
			#			1SG machete-PL and knife-PL put.up.PL.OBJ-PST .
			#			I put up the machetes and the knifes .
			
			if src_indices and tgt_indices:
				src_index = src_indices.pop()
				tgt_index = tgt_indices.pop()
			else:
				break
			
			
		
		# If there is only source index remaining, but multiple target indices,
		# map this source to all the remaining targets.
		
		if len(tgt_indices) >= 1:
			for tgt_index in tgt_indices:
				if tgt_sequence[tgt_index].morphequals(src_sequence[src_index], **kwargs):
					yield((src_index, tgt_index))
				
		# Otherwise, if there are remaining source indices, map them to the last remaining
		# target index.
		
		if len(src_indices) >= 1:
			for src_index in src_indices:
				if src_sequence[src_index].morphequals(tgt_sequence[tgt_index], **kwargs):
					yield((src_index, tgt_index))
	else:
		pass
	
		
class IGTException(Exception):
	def __init__(self, m = ''):
		Exception.__init__(self, m)
		
class IGTTier(list):
	'''
	Class to hold individual tiers of IGT instances.
	'''
	
	
	
	def __init__(self, seq=[], kind = None):
		self.kind = kind
		list.__init__(self, seq)
		
	@staticmethod
	def fromString(string):
		'''
		
		Convenience method to create a tier from a string. Helpful for testing.
		
		@param string: whitespace separated string to turn into a tier
		'''
		tier = IGTTier()
		for token in string.split():
			t = IGTToken(token)
			tier.append(t)
		return tier
		
	def append(self, item):
		if not isinstance(item, IGTToken):
			raise IGTException('Attempt to add non-IGTToken to IGTTier')
		else:
			list.append(self, item)
			
	def __str__(self):
		return '<IGTTier kind=%s len=%d>' % (self.kind, len(self))
	
	def __contains__(self, item, **kwargs):		
		'''
		Search for an item, and return True/False whether it is contained or not. 
		
		@param item:
		@param lowercase:
		'''
		result = self.search(item, **kwargs)
		if result is None:
			return False
		else:
			return True

	def search(self, other, **kwargs):
		'''
		Search for an other in the tier. If it is not found, return None, otherwise
		return a list of integer indices (can be zero, so use contains to check for equality) 
		
		@param other: IGTToken or string to search for
		@param lowercase: Do a case-insensitive comparison or not
		@param stem: Do stemming
		@param deaccent: Remove accents for comparison
		'''
		
		found = []
		
		for i in range(len(self)):
			my_token = self[i]
			
			if my_token.morphequals(other, **kwargs):
				found.append(i)
			
		# If we haven't returned true yet, return false
		return found



class IGTToken(object):
	
	
	def __init__(self, seq='', idx=None):
		self.idx = idx
		self.seq = seq
		self.attrs = {}
		
	def split(self):
		return self.seq.split()
		
	def morphs(self):
		for elt in re.split(r'[-.():]', self.seq):
			yield Morph(elt, self)
	
	def __repr__(self):
		return '<IGTToken (%s): %s %s>' % (self.idx, self.seq, self.attrs)
	
	def __str__(self):
		return self.seq
	
	def lower(self):
		return self.seq.lower()
	
	def __eq__(self, o):
		if isinstance(o, IGTToken):
			return self.seq == o.seq
		else:
			return self.seq == o
		
		
	def morphequals(self, o, **kwargs):
		'''
		This function returns True if any morph contained in this token equals
		any morph contained in the other token 
		
		@param o:
		@param lowercase:
		@param stem:
		@param deaccent:
		'''
		# Keep track of whether we've found a match or not.
		found = False
		
		# First, get our own morphs.
		if kwargs.get('tokenize_src', True):
			morphs = self.morphs()
			
		# If we're not tokenize ourself, make one single
		# morph out of ourself. 
		else:
			morphs = [Morph(self.seq)]

		for morph in morphs:
		
			# If the other object is also a token,
			# get its morphs as well.
			if isinstance(o, IGTToken):
				
				# Split the target into morphs if we're tokenizing...
				if kwargs.get('tokenize_tgt', True):
					o_morphs = o.morphs()
					
				# Otherwise make it a single morph.
				else:
					o_morphs = [Morph(o.seq)]
					
				for o_morph in o_morphs:
					if string_compare_with_processing(morph.seq, o_morph.seq, **kwargs):
						found = True
						break
					
			
			# If the other object is a morph, just compare it to what we have.
			elif isinstance(o, Morph):
				if string_compare_with_processing(morph.seq, o.seq, **kwargs):
					found = True
					break
				
			else:
				raise IGTException('Attempt to morphequals IGTToken with something other than Token or Morph')
		
		# Return whether we found a match among the morphs or not.
		return found
				

		
			
		
		
	def set_attr(self, key, value):
		self.attrs[key] = value
		
	def get_attr(self, key):
		return self.attrs[key]
	
def string_compare_with_processing(s1, s2, **kwargs):
	
	# Before we do anything, see if we have a match.
	if s1 == s2:
		return True
	
	if kwargs.get('lowercase', True):
		s1 = s1.lower()
		s2 = s2.lower()
		
	# Keep checking...
	if s1 == s2:
		return True
		
	if kwargs.get('deaccent', True):
		s1 = unidecode(s1)
		s2 = unidecode(s2)
		
		
	# Do various types of increasingly aggressive stemming...
	if kwargs.get('stem', True):
		stem1 = lemmatize_token(s1)
		stem2 = lemmatize_token(s2)
		
		if stem1 == stem2:
			return True

		stem1 = stem_token(s1)
		stem2 = stem_token(s2)
			
		if stem1 == stem2:
			return True
		
		stem1 = lemmatize_token(s1, 'a')
		stem2 = lemmatize_token(s2, 'a')
			
		if stem1 == stem2:
			return True
	
		stem1 = lemmatize_token(s1, 'n')
		stem2 = lemmatize_token(s2, 'n')
		
		if stem1 == stem2:
			return True
	
	# We could do the gram stuff here, but it doesn't work too well.
	# Instead, let's try doing it as a second pass to pick up stil-unaligned
	# words.
	if kwargs.get('gloss_on',False):
		gloss_grams_1 = sub_grams(s1)
		gloss_grams_2 = sub_grams(s2)
		
		if s2.strip() and s2 in gloss_grams_1:
			return True
		if s1.strip() and s1 in gloss_grams_2:
			return True
					
		
		
	return s1 == s2
	
	
		
class Morph:
	'''
	This class is what makes up an IGTToken. Should be comparable to a token
	'''
	def __init__(self, seq, parent=None):
		self.parent = parent
		self.seq = seq
		
	def __eq__(self, o):
		if isinstance(o, Morph):			
			return self.seq == o.seq
		else:
			raise IGTException('Attempt to compare Morph to something other than Morph')
		
	def morphequals(self, o, **kwargs):
		if isinstance(o, Morph):
			return self.seq == o.seq
		elif isinstance(o, IGTToken):
			return o.morphequals(self, **kwargs)
		else:
			raise IGTException('Attempt to morphequals Morph with something other than Morph or IGTToken')
		
	
		
#===============================================================================
# Unit tests
#===============================================================================
		
class MorphTestCase(unittest.TestCase):
	def setUp(self):
		self.m1 = Morph('the', None)
		self.m2 = Morph('dog', None)
		self.m3 = Morph('the', None)
	def runTest(self):
		assert self.m1 != self.m2
		assert self.m1 == self.m3
		
class IGTTokenTestCase(unittest.TestCase):
	def runTest(self):
		t1 = IGTToken('your')
		t2 = IGTToken('your')
		t3 = IGTToken('you-are')
		t4 = IGTToken('you')
		t5 = IGTToken('Your')
		t6 = IGTToken('1SG.You.ARE')
		
		assert t1 == t2
		assert t1 != t3
		assert t4.morphequals(t3)
		assert t3.morphequals(t4)
		assert not t3.morphequals(t1)
		assert not t5.morphequals(t1, lowercase=False, stem=False)
		assert t5.morphequals(t1, lowercase=True, stem=False)
		assert t6.morphequals(t4, lowercase=True, stem=False)
		
class MorphTokenCompare(unittest.TestCase):
	def runTest(self):
		t1 = IGTToken('THE.horse')
		m1 = Morph('Horse', t1)
		
		self.assertEqual(m1.parent, t1)
		self.assertTrue(t1.morphequals(m1, lowercase=True, stem=False, deaccent=False))
		self.assertFalse(t1.morphequals(m1, lowercase=False, stem=False))
		self.assertRaises(IGTException, lambda: m1.morphequals('string'))
		self.assertRaises(IGTException, lambda: t1.morphequals('string'))
		
class TestTierSearch(unittest.TestCase):
	def runTest(self):
		t1 = IGTTier.fromString('he Det.ACC horse-ACC house-ACC see-CAUSE-PERF .')
		t2 = IGTTier.fromString('He showed the horse the house .')
		
		t3 = IGTTier.fromString('lizard-PL and gila.monster-PL here rest.PRS .')
		t4 = IGTTier.fromString('The lizards and the gila monsters are resting here .')
		
		o1 = IGTToken('horse')
		o2 = IGTToken('gila.monster-PL')
		
		m1 = Morph('horse')
		m2 = Morph('the')
		m3 = Morph('acc')
		
		self.assertEquals(t1.search(o1, lowercase=False), [2])
		self.assertEquals(t1.search(m1, lowercase=False), [2])
		self.assertEquals(t2.search(m2, lowercase=False), [2,4])
		self.assertEquals(t1.search(m3, lowercase=True), [1,2,3])
		
		self.assertEquals(t4.search(o2, stem=False), [4])
		self.assertEquals(t3.search(o2, stem=False), [0, 2])
		
		
class TestMatchMultiples(unittest.TestCase):
	def runTest(self):
		t1 = IGTTier.fromString('the dog.NOM bit-PST the cat-OBJ')
		t2 = IGTTier.fromString('the dog Bites The cat')
		
		t3 = IGTTier.fromString('your house is on your side of the street')
		t4 = IGTTier.fromString('your house is on your side of your street')
		
		t5 = IGTTier.fromString('the dog.NOM ran alongside the other dog')
		t6 = IGTTier.fromString('the dog runs alongside the other dog')
		
		t7 = IGTTier.fromString('lizard-PL and gila.monster-PL here rest.PRS .')
		t8 = IGTTier.fromString('The lizards and the gila monsters are resting here .')
		
		t10 = IGTTier.fromString('Peter something buy.PRS and something sell.PRS .')
		t9 = IGTTier.fromString('Pedro buys and sells something .')
		
		o1 = IGTToken('the')
		o2 = IGTToken('your')
		o3 = IGTToken('dog.NOM')
		o4 = IGTToken('gila.monster-PL')
		o5 = IGTToken('something')
		
		
		
		self.assertEquals(set(match_multiples(o1, t1, t2, lowercase=True)), set([(0,0), (3,3)]))
		self.assertEquals(set(match_multiples(o2, t3, t4)), set([(0, 0), (4, 4), (4, 7)]))
		
		dogmatches = set(match_multiples(o3, t5, t6))
		
		self.assertEquals(dogmatches, set([(1, 1), (6, 6)]))
		
		# the "gila.monster-PL" should only match to "gila" with stemming off.
		self.assertEquals(set(match_multiples(o4, t7, t8, stem=False)), set([(2, 4)]))
		
				
		t1 = IGTTier.fromString('1SG machete-PL and knife-PL put.up.PL.OBJ-PST .')
		t2 = IGTTier.fromString('I put up the machetes and the knifes .')
		
		o1 = IGTToken('put.up.PL.OBJ-PST')
		self.assertEquals(set(match_multiples(o1, t1, t2)), set([(4,1),(4,2)]))
		
		# The "Something" should align from the target line to both sources.
		self.assertEquals(set(match_multiples(o5, t10, t9)), set([(1,4),(4,4)]))
		
		
class TestAllEquals(unittest.TestCase):
	def runTest(self):
		o1 = IGTToken('gila.monster-PL')
		o2 = IGTToken('gila')
		o3 = IGTToken('lizard-PL')
		
		comparator = lambda x, y: x.morphequals(y)
		
		self.assertFalse(alltrue([o1,o2,o3], comparator))
		self.assertTrue(alltrue([o1,o2], comparator))
		self.assertTrue(alltrue([o1,o3], comparator))
		
class AlignGrams(unittest.TestCase):
	def runTest(self):
		o1 = IGTToken('I')
		o2 = IGTToken('1SG')
		
		self.assertTrue(o2.morphequals(o1, gloss_on=True, lowercase=True))
		
class AlignContains(unittest.TestCase):
	def runTest(self):
		a1 = Alignment([(2, 5), (3, 4), (1, 1), (4, 3)])
		
		self.assertTrue(a1.contains_src(2))
		self.assertTrue(a1.contains_src(4))
		