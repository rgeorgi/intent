'''
Created on Feb 17, 2015

@author: rgeorgi
'''

import unittest
from unittest.case import TestCase
from igt.rgxigt import RGTier
from utils.token import tokenize_string, morpheme_tokenizer,\
	whitespace_tokenizer, tokenize_item
from alignment.Alignment import Alignment

class MorphAlignException(Exception):
	pass

class Sentence(RGTier):
	'''
	Set of words, which may have sub-word morpheme-level components. 
	'''
	
	def __init__(self, items=[], **kwargs):
		RGTier.__init__(self, items=items, **kwargs)
		
	@classmethod
	def from_string(cls, string):
		return cls(tokenize_string(string, whitespace_tokenizer))
	
	def morphs(self):
		'''
		Return a list of all the morphs in this sentence.
		'''
		sent_morphs = Sentence(type='morphs')
		
		last_index = 1
		for word in self:

			morphs = tokenize_item(word, morpheme_tokenizer)
			for morph in morphs:
				morph.index = last_index
				morph.parent = word
				
				
				morph.id = word.tier.id+'m'+str(last_index)
				sent_morphs.add(morph)
				
				last_index += 1
				
		return sent_morphs
	
	def align_morphs(self, msent):
		'''
		Assuming a sentence consisting of sub-portions of this sentence, attempt to align 
		the pieces from left to right.
		'''
		
		my_morphs = self.morphs()

		sent_to_morph_aln = Alignment()

		for my_morph, their_morph in zip(my_morphs, msent):
			
			# If the morphemes do not align, raise an exception.
			if my_morph.content != their_morph.content:
				raise MorphAlignException('Morphemes do not align with sentence.')
			
			sent_to_morph_aln.add((my_morph.parent.index, their_morph.index))

		return sent_to_morph_aln
		
			
			

	

class MorphTest(TestCase):
	
	def runTest(self):
		gs = Sentence.from_string('how-part-fss do-hab-past my grand-mother when')
		gm = Sentence.from_string('how part fss do hab past my grand mother when')
		
		msa_gold = Alignment([(1,1),(1,2),(1,3),(2,4),(2,5),(2,6),(3,7),(4,8),(4,9),(5,10)])		
		msa_test = gs.align_morphs(gm)
		
		self.assertEqual(msa_gold, msa_test)
		
class CapsTest(TestCase):
	
	def runTest(self):
		gs = Sentence.from_string('this')
		gm = Sentence.from_string('This')
		
		# Assert that an attempt to align these two when the capitalization 
		# disagrees and lowercase is not specified will raise an exception.
		self.assertRaises(MorphAlignException, gm.align_morphs, gs)
		
		
class MisalignedTest(TestCase):
	
	def runTest(self):
		gs = Sentence.from_string('this-is a')
		gm = Sentence.from_string('this')
		
		self.assertRaises(MorphAlignException, gm.align_morphs, gs)
		