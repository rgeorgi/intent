'''
Created on Mar 7, 2014

@author: rgeorgi
'''
from alignment.Alignment import Alignment, AlignedSent
import re
from alignment.align import stem_token
from unidecode import unidecode
import sys

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
	
	def gloss_heuristic_alignments(self, lowercase=True, stem=True, morph=True):
		return [inst.gloss_heuristic_alignment(lowercase=lowercase, stem=stem, morph=morph) for inst in self]
		
		
class IGTInstance(list):
	'''
	Container class for an IGT instance and all the dealings that will go on inside it.
	'''
	
	def __init__(self, seq=[], id = None):
		self._id = id
		self.glossalign = Alignment()
		self.langalign = Alignment()
		list.__init__(self, seq)
		
	def get_gloss_align_sent(self):
		# TODO: Again with the zero-indexing...
		return AlignedSent(self.gloss()[0], self.trans()[0], self.glossalign)
	
	def get_lang_align_sent(self):
		# TODO: Guess what...
		return AlignedSent(self.gloss()[0], self.trans()[0], self.langalign)
		
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
	
	def __str__(self):
		ret_str = ''
		for kind in set([tier.kind for tier in self]):
			ret_str += '%s,'%str(kind)
		return '<IGTInstance %d: %s>' % (self._id, ret_str[:-1])
	
	def gloss_heuristic_alignment(self, lowercase=True, remove_punc=True, morph=True, stem=True, deaccent=True):
		
		# FIXME: Make sure that when there are multiple occurrences of a token, they are aligned left-to-right.
		
		# TODO: Again, we're working with zero-indices here... not liking it.
		gloss = self.gloss()[0]
		trans = self.trans()[0]
		
		aln = Alignment()
		
		for gloss_i in range(len(gloss)):
			gloss_token = gloss[gloss_i]
			
			gloss_token.set_attr('id', self._id)
			
			#===================================================================
			# Before we even take a look at the morphs, just look at the
			# token on its own.
			#===================================================================
						
			# TODO: Find a way to match left-to-right just once, and not repeat it for each time.
			#       perhaps only start from the current instance?
						
			matches = list(match_multiples(gloss_token, gloss, trans, lowercase, stem, deaccent))
			if matches:
				for a, b in matches[:1]:
					aln.add((a+1,b+1))
							
			
			#===================================================================
			# If we didn't find it unmorphed, let's look through the morphemes.
			#===================================================================
			if  morph:
				morphs = gloss_token.morphs()
				
				# Add the morphs to the token for later debugging
				gloss_token.set_attr('morphs', morphs)
				
				
				for morph in morphs:
					matches = list(match_multiples(morph, gloss, trans, lowercase, stem, deaccent))
					if matches:
						for a, b in matches:
							aln.add((a+1, b+1))
				
				
		return AlignedSent(gloss, trans, aln)
		
				
def match_multiples(item, src_sequence, tgt_sequence, lowercase=False, stem=False, deaccent=False):
	'''
	Code to take an item with source and target sequences, and match
	them left to right as necessary.
	
	@param item:
	@param src_sequence:
	@param tgt_sequence:
	'''
	
	src_indices = src_sequence.search(item, lowercase, stem, deaccent)
	tgt_indices = tgt_sequence.search(item, lowercase, stem, deaccent)
	
	if src_indices and tgt_indices:
		
		# Loop until we are out of indices on one side
		while src_indices and tgt_indices:
			
			# Start by popping the leftmost indices
			src_index = src_indices.pop(0)		
			tgt_index = tgt_indices.pop(0)
			
			yield((src_index, tgt_index))
			
		
		# Map our last src index to all the remaining tgt_indices.
		for tgt_index in tgt_indices:
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
		
	def append(self, item):
		if not isinstance(item, IGTToken):
			raise IGTException('Attempt to add non-IGTToken to IGTTier')
		else:
			list.append(self, item)
			
	def __str__(self):
		return '<IGTTier kind=%s len=%d>' % (self.kind, len(self))
	
	def __contains__(self, item, lowercase=False):		
		'''
		Search for an item, and return True/False whether it is contained or not. 
		
		@param item:
		@param lowercase:
		'''
		result = self.search(item, lowercase)
		if result is None:
			return False
		else:
			return True
	
	def search(self, item, lowercase=False, stem=False, deaccent=False):
		'''
		Search for an item in the tier. If it is not found, return None, otherwise
		return a list of integer indices (can be zero, so use contains to check for equality) 
		
		@param item: IGTToken or string to search for
		@param lowercase: Do a case-insensitive comparison or not
		@param stem: Do stemming
		@param deaccent: Remove accents for comparison
		'''
		
		found = []
		
		for i in range(len(self)):
			my_item = self[i]
			
			# Do a case-insensitive comparison if asked
			if lowercase:
				item = item.lower()
				my_item = my_item.lower()
		
			if stem:
				item = stem_token(item)
				my_item = stem_token(my_item)
				
			if deaccent:
				item = unidecode(item)
				my_item = unidecode(my_item)
	
			# Now, see if the item is there
			if my_item == item:
				found.append(i)
			
		# If we haven't returned true yet, return false
		return found
	
	def index(self, item, lowercase=False):
		result = self.search(item, lowercase)
		if result:
			return result
		else:
			raise IGTException('Tier does not contain item %s' % (item))
			
		
class IGTToken(object):
	
	
	def __init__(self, seq='', idx=None):
		self.idx = idx
		self.seq = seq
		self.attrs = {}
		
	def split(self):
		return self.seq.split()
		
	def morphs(self):
		return re.split(r'[-.()]', self.seq)
	
	def __repr__(self):
		return '<IGTToken (%d): %s %s>' % (self.idx, self.seq, self.attrs)
	
	def __str__(self):
		return self.seq
	
	def lower(self):
		return self.seq.lower()
	
	def __eq__(self, o):
		if not isinstance(o, IGTToken):
			return self.seq == o
		else:
			return self.seq == o.seq
		
	def set_attr(self, key, value):
		self.attrs[key] = value
		
	def get_attr(self, key):
		return self.attrs[key]
	
		
		