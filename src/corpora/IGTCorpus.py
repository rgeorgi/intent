'''
Created on Mar 7, 2014

@author: rgeorgi
'''
from alignment.Alignment import Alignment, AlignedSent
import re
from unidecode import unidecode
import sys

import unittest
from utils.string_utils import stem_token, lemmatize_token, tokenize_string,\
	Token, morpheme_tokenizer
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
	
	def gloss_heuristic_alignments(self, **kwargs):
		return [inst.gloss_heuristic_alignment(**kwargs) for inst in self]
	
		
		
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
		a = AlignedSent(self.gloss[0], self.trans[0], self.glossalign)
		a.attrs = self.attrs
		return a
	
	def get_lang_align_sent(self):
		# TODO: Guess what...
		a = AlignedSent(self.gloss[0], self.trans[0], self.langalign)
		a.attrs = self.attrs
		return a
		
	def append(self, item):
		if not isinstance(item, IGTTier):
			raise IGTException('Attempt to append a non-IGTTier instance to an IGTInstance')
		list.append(self, item)
	
	@property	
	def gloss(self):
		return [tier for tier in self if tier.kind == 'gloss']
	
	@property
	def trans(self):
		return [tier for tier in self if tier.kind == 'trans']
	
	@property
	def lang(self):
		return [tier for tier in self if tier.kind == 'lang']
		
	def gloss_text(self, **kwargs):
		return [tier.text(**kwargs) for tier in self if tier.kind == 'gloss']
	
	def trans_text(self, **kwargs):
		return [tier.text(**kwargs) for tier in self if tier.kind == 'trans']
	
	def set_attr(self, key, val):
		self.attrs[key] = val
		
	def get_attr(self, key):
		return self.attrs[key]
	

	
	def __str__(self):
		ret_str = ''
		for tier in self:
			ret_str += '%s,'%str(tier)
		return '<IGTInstance %s: %s>' % (self._id, ret_str[:-1])
	
	def gloss_heuristic_alignment(self, **kwargs):
		
		# FIXME: Make sure that when there are multiple occurrences of a token, they are aligned left-to-right.
		
		# TODO: Again, we're working with zero-indices here... not liking it.
		gloss = self.gloss[0]
		trans = self.trans[0]
		
		aln = Alignment()
		
		#=======================================================================
		#  1) Get the morphs for each of the tiers
		#
		#  2) Make a first pass, aligning each morph with the first unaligned
		#     morph on the other side.
		#
		#  3) Make subsequent passes to pick up any tokens not aligned. 
		#
		#=======================================================================
		
		if kwargs.get('tokenize', True):
			gloss_tokens = gloss.morphs()
			trans_tokens = trans.morphs()
		else:
			gloss_tokens = gloss
			trans_tokens = trans
		
		alignments = get_alignments(gloss_tokens, trans_tokens, **kwargs)
		
		for a, b in alignments:
			aln.add((a, b))
			
			
		#=======================================================================
		# Do the gram matching if it's enabled.
		#=======================================================================
		
		if kwargs.get('grams_on'):
			kwargs['gloss_on'] = True
			gloss_alignments = get_alignments(gloss_tokens, trans_tokens, **kwargs)
			
			for a, b in gloss_alignments:
				aln.add((a, b))

							
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

	

def get_alignments(gloss_morphs, trans_morphs, iteration=1, **kwargs):
	
	alignments = set([])
		
	# For the second iteration
	if iteration>1:
		gloss_morphs = gloss_morphs[::-1]
		trans_morphs = trans_morphs[::-1]
	
	for gloss_morph in gloss_morphs:
		
		for trans_morph in trans_morphs:
			
			if gloss_morph.morphequals(trans_morph, **kwargs):
				# Get the alignment count
				trans_align_count = trans_morph.attrs.get('align_count', 0)
				gloss_align_count = gloss_morph.attrs.get('align_count', 0)
				
				
				# Only align with tokens 
				if trans_align_count == 0:
					trans_morph.attrs['align_count'] = trans_align_count+1
					gloss_morph.attrs['align_count'] = gloss_align_count+1
					alignments.add((gloss_morph.index, trans_morph.index))
					
					# Stop aligning this gloss token for this iteration.
					break
				
				# If we're on the second pass and the gloss wasn't aligned, align
				# it to whatever remains.
				elif gloss_align_count == 0 and iteration == 2:
					trans_morph.attrs['align_count'] = trans_align_count+1
					gloss_morph.attrs['align_count'] = gloss_align_count+1
					alignments.add((gloss_morph.index, trans_morph.index))
				
				
	
	if iteration == 2:
		return alignments
	else:
		return alignments | get_alignments(gloss_morphs, trans_morphs, iteration+1, **kwargs)
	
		
	
	
				


	
		
class IGTException(Exception):
	def __init__(self, m = ''):
		Exception.__init__(self, m)
		
class IGTTier(list):
	'''
	Class to hold individual tiers of IGT instances.
	'''
	
	
	
	def __init__(self, seq='', **kwargs):
		self.kind = kwargs.get('kind', None)
		list.__init__(self, seq)
		
	@classmethod
	def fromString(cls, string, **kwargs):
		'''
		
		Convenience method to create a tier from a string. Helpful for testing.
		
		@param string: whitespace separated string to turn into a tier
		'''
		tier = cls(**kwargs)
		
		for token in tokenize_string(string):
			t = IGTToken.fromTokn(token)
			tier.append(t)
		return tier
		
	def append(self, item):
		if not isinstance(item, IGTToken):
			raise IGTException('Attempt to add non-IGTToken to IGTTier')
		else:
			list.append(self, item)
			
	def __str__(self):
		return '<IGTTier kind=%s len=%d>' % (self.kind, len(self))
	
	def text(self, **kwargs):
		text = ' '.join([token.seq for token in self]).strip()
		if kwargs.get('lowercase', True):
			text = text.lower()
		return text
	
	
	def morphs(self):
		'''
		Return the sequence of morphs for this tier.
		'''
		ret_list = []
		for token in self:
			ret_list.extend(token.morphs())
		return ret_list


class Span(object):
	def __init__(self, start, stop):
		self.start = start
		self.stop = stop

class IGTToken(Token):
	
	def __init__(self, seq='', parent=None, span=None, index=None):			
		self._attrs = {}		
		self.parent = parent
		Token.__init__(self, seq, span, index)
		
	@classmethod
	def fromTokn(cls, token, parent=None):
		return cls(seq=token.seq, parent=parent, span=token.span, index=token.index)
		
	def split(self):
		return self.seq.split()
		
	def morphs(self):
		morphs = list(tokenize_string(self.seq, morpheme_tokenizer))
		
		# If the tokenization yields no tokens, just return the string.
		if self.seq and len(morphs) == 0:
			yield Morph(self.seq, parent=self)
			

		for morph in morphs:
			yield(Morph.fromToken(morph, parent=self))		
		
	
	def __repr__(self):
		return '<IGTToken: [%s] %s>' % (self.index, self.seq)
	
	def __str__(self):
		return self.__repr__()
	
	def lower(self):
		return self.seq.lower()
	
	def __eq__(self, o):
		if isinstance(o, IGTToken):
			return self.seq == o.seq
		else:
			return self.seq == o
		
	def text(self, **kwargs):
		text = self.seq
		if kwargs.get('lowercase', True):
			text = text.lower()
		return text
		
	def __hash__(self):
		return id(self)
		
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
	
	
		
class Morph(Token):
	'''
	This class is what makes up an IGTToken. Should be comparable to a token
	'''
	def __init__(self, seq='', span=None, parent=None):
		self.parent = parent
		index = parent.index if parent else None
		Token.__init__(self, seq, span, index)
		
		
		
	def __eq__(self, o):
		if isinstance(o, Morph):			
			return self.seq == o.seq
		else:
			raise IGTException('Attempt to compare Morph to something other than Morph')
		
	def morphequals(self, o, **kwargs):
		if isinstance(o, Morph):
			return string_compare_with_processing(self.seq, o.seq, **kwargs)
		elif isinstance(o, IGTToken):
			return o.morphequals(self, **kwargs)
		else:
			raise IGTException('Attempt to morphequals Morph with something other than Morph or IGTToken')
		
	@classmethod
	def fromToken(cls, token, parent):
		return cls(token.seq, token.span, parent)
		
	def __str__(self):
		return '<Morph: %s>' % self.seq
		
	
		
#===============================================================================
# Unit tests
#===============================================================================
		
class MorphTestCase(unittest.TestCase):
	def setUp(self):
		self.m1 = Morph('the')
		self.m2 = Morph('dog')
		self.m3 = Morph('the')
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
		m1 = Morph('Horse', parent=t1)
		
		self.assertEqual(m1.parent, t1)
		self.assertTrue(t1.morphequals(m1, lowercase=True, stem=False, deaccent=False))
		self.assertFalse(t1.morphequals(m1, lowercase=False, stem=False))
		self.assertRaises(IGTException, lambda: m1.morphequals('string'))
		self.assertRaises(IGTException, lambda: t1.morphequals('string'))
		

		
		
class AlignGrams(unittest.TestCase):
	def runTest(self):
		o1 = IGTToken('I')
		o2 = IGTToken('1SG')
		
		self.assertTrue(o2.morphequals(o1, gloss_on=True, lowercase=True))
		
class getAlignmentsTest(unittest.TestCase):
	def runTest(self):
		t1 = IGTTier.fromString('This taxi-driver to-me seems to-be tired')
		t2 = IGTTier.fromString("b\"	'This taxi driver seems to me to be tired")
		
		o1 = IGTToken('to-me')
		
		self.assertEquals(get_alignments(t1.morphs(), t2.morphs()), set([(1,2),(2,3),(2,4),(3,6),(3,7),(4,5),(5,8),(5,9),(6,10)]))
		
		t3 = IGTTier.fromString('your house is on your side of the street')
		t4 = IGTTier.fromString('your house is on your side of your street')
		
		self.assertEquals(get_alignments(t3.morphs(), t4.morphs()), {(5, 5), (6, 6), (4, 4), (7, 7), (9, 9), (2, 2), (1, 1), (5, 8), (3, 3)})
		
		t5 = IGTTier.fromString('the dog.NOM ran alongside the other dog')
		t6 = IGTTier.fromString('the dog runs alongside the other dog')
		
		self.assertEquals(get_alignments(t5.morphs(), t6.morphs()), {(1,1), (2,2), (3,3), (4,4), (5, 5), (6, 6), (7, 7)})
		
		t7 = IGTTier.fromString('lizard-PL and gila.monster-PL here rest.PRS .')
		t8 = IGTTier.fromString('The lizards and the gila monsters are resting here .')
		
		self.assertEquals(get_alignments(t7.morphs(), t8.morphs()), {(1,2), (2, 3), (3, 5), (3, 6), (4, 9), (5, 8), (6, 10)})
		
		t10 = IGTTier.fromString('Peter something buy.PRS and something sell.PRS .')
		t9 = IGTTier.fromString('Pedro buys and sells something .')
		
		self.assertEquals(get_alignments(t10.morphs(), t9.morphs()), {(2,5), (3,2), (4,3), (5, 5), (6, 4), (7, 6)})
		
		
class AlignContains(unittest.TestCase):
	def runTest(self):
		a1 = Alignment([(2, 5), (3, 4), (1, 1), (4, 3)])
		
		self.assertTrue(a1.contains_src(2))
		self.assertTrue(a1.contains_src(4))
		