'''
Created on Mar 7, 2014

@author: rgeorgi
'''
from alignment.Alignment import Alignment, AlignedSent
import re
import sys

import unittest
from utils.Token import Token, TokenException
from utils.string_utils import string_compare_with_processing
from utils.token_utils import tokenize_string, morpheme_tokenizer


class IGTCorpus(list):
	'''
	Object that will hold a corpus of IGT instances.
	'''

	def __init__(self, seq = []):
		list.__init__(self, seq)

	def gloss_alignments(self):
		return [inst.gloss_alignments() for inst in self]

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
		
	def gloss_alignments(self):
		a = AlignedSent(self.gloss, self.trans, self.glossalign)
		a.attrs = self.attrs
		return a
	
	def get_lang_align_sent(self):
		a = AlignedSent(self.gloss, self.trans, self.langalign)
		a.attrs = self.attrs
		return a
		
	def append(self, item):
		if not isinstance(item, IGTTier):
			raise IGTException('Attempt to append a non-IGTTier instance to an IGTInstance')
		list.append(self, item)
	
	@property	
	def gloss(self):
		return [tier for tier in self if tier.kind == 'gloss'][0]
	
	@property
	def trans(self):
		return [tier for tier in self if tier.kind == 'trans'][0]
	
	@property
	def lang(self):
		return [tier for tier in self if tier.kind == 'lang'][0]
		
	@property
	def gloss_texts(self, **kwargs):
		return self.gloss.text(**kwargs)	
	
	@property
	def trans_texts(self, **kwargs):
		return self.trans.text(**kwargs)
	
	def set_attr(self, key, val):
		self.attrs[key] = val
		
	def get_attr(self, key):
		return self.attrs[key]
	

	
	def __str__(self):
		ret_str = ''
		for tier in self:
			ret_str += '%s,'%str(tier)
		return '<IGTInstance %s: %s>' % (self._id, ret_str[:-1])
	
	def lang_heuristic_alignment(self, **kwargs):
		ga = self.gloss_heuristic_alignment(**kwargs).aln
		la = self.langalign
		
		#=======================================================================
		# If we don't have a language-gloss alignment, assume 1:1, otherwise
		# raise an exception.
		#=======================================================================
		if not la:
			if len(self.gloss) != len(self.lang):
				raise IGTAlignmentException('Language line and gloss line not the same length at %s' % self._id)
			else:
				return AlignedSent(self.lang, self.trans, ga)

	@property
	def id(self):
		return self._id
	
	def gloss_heuristic_alignment(self, **kwargs):
		if hasattr(self, '_gha'):
			return self._gha
		else:
			return self.gloss_heuristic_alignment_h(**kwargs)
	
	def gloss_heuristic_alignment_h(self, **kwargs):
		
		# TODO: Again, we're working with zero-indices here... not liking it.
		gloss = self.gloss
		trans = self.trans
		
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
		
		if kwargs.get('grams_on', True):
			kwargs['gloss_on'] = True
			gloss_alignments = get_alignments(gloss_tokens, trans_tokens, **kwargs)
			
			for a, b in gloss_alignments:
				aln.add((a, b))

							
		a = AlignedSent(gloss, trans, aln)
		a.attrs = self.attrs
		self._gha = a
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

	

def get_alignments(gloss_tokens, trans_tokens, iteration=1, **kwargs):
	
	alignments = set([])
		
	# For the second iteration
	if iteration>1:
		gloss_tokens = gloss_tokens[::-1]
		trans_tokens = trans_tokens[::-1]
	
	for gloss_token in gloss_tokens:
		
		for trans_token in trans_tokens:
			
			if gloss_token.morphequals(trans_token, **kwargs):
				# Get the alignment count
				trans_align_count = trans_token.attrs.get('align_count', 0)
				gloss_align_count = gloss_token.attrs.get('align_count', 0)
				
				
				# Only align with tokens 
				if trans_align_count == 0 or kwargs.get('no_multiples', False):
					trans_token.attrs['align_count'] = trans_align_count+1
					gloss_token.attrs['align_count'] = gloss_align_count+1
					alignments.add((gloss_token.index, trans_token.index))
					
					# Stop aligning this gloss token for this iteration.
					break
				
				# If we're on the second pass and the gloss wasn't aligned, align
				# it to whatever remains.
				elif gloss_align_count == 0 and iteration == 2:
					trans_token.attrs['align_count'] = trans_align_count+1
					gloss_token.attrs['align_count'] = gloss_align_count+1
					alignments.add((gloss_token.index, trans_token.index))
				
				
	
	if iteration == 2 or kwargs.get('no_multiples', False):
		return alignments
	else:
		return alignments | get_alignments(gloss_tokens, trans_tokens, iteration+1, **kwargs)
	
		
	
	
				



		
class IGTException(Exception):
	def __init__(self, m = ''):
		Exception.__init__(self, m)
		
class IGTAlignmentException(IGTException):
	pass
		
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
	
	
	def morphs(self, **kwargs):
		'''
		Return the sequence of morphs for this tier.
		'''
		ret_list = []
		for token in self:
			ret_list.extend(token.morphs(**kwargs))
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
		
	def morphs(self, **kwargs):
		for morph in self.morphed_tokens():
			if kwargs.get('lowercase'):
				morph = Morph(morph.seq.lower(), morph.span, morph.parent)
			yield morph
		
	def morphed_tokens(self):
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

	def set_attr(self, key, value):
		self.attrs[key] = value
		
	def get_attr(self, key):
		return self.attrs[key]
	

	
	
		
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
		
		self.assertEqual(t1, t2)
		self.assertNotEqual(t1, t3)
		
		self.assertFalse(t4.morphequals(t3))
		self.assertFalse(t3.morphequals(t4))
		self.assertFalse(t3.morphequals(t1))
		self.assertFalse(t5.morphequals(t1, lowercase=False, stem=False))
		self.assertTrue(t5.morphequals(t1, lowercase=True, stem=False))
		self.assertFalse(t6.morphequals(t4, lowercase=True, stem=False))
		
		#=======================================================================
		# Test stemming
		#=======================================================================
		t1 = IGTToken('passed')
		t2 = IGTToken('Pass')
		
		self.assertTrue(t1.morphequals(t2, lowercase=True, stem=True))
		
class MorphTokenCompare(unittest.TestCase):
	def runTest(self):
		t1 = IGTToken('THE.horse')
		m1 = Morph('Horse', parent=t1)
		
		self.assertEqual(m1.parent, t1)
		self.assertFalse(t1.morphequals(m1, lowercase=True, stem=False, deaccent=False))
		self.assertFalse(t1.morphequals(m1, lowercase=False, stem=False))
		self.assertRaises(TokenException, lambda: m1.morphequals('string'))
		self.assertRaises(TokenException, lambda: t1.morphequals('string'))		
		
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
		