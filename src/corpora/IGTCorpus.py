'''
Created on Mar 7, 2014

@author: rgeorgi
'''
from alignment.Alignment import Alignment, AlignedSent
import re
import sys

import unittest
from utils.token import Token, TokenException, Morph, tokenize_string,\
	morpheme_tokenizer, GoldTagPOSToken, whitespace_tokenizer, POSToken
from igt.igtutils import merge_lines, clean_lang_string, clean_gloss_string,\
	clean_trans_string, hyphenate_infinitive
from _io import StringIO
from igt.grams import write_gram
from _collections import defaultdict
import xigt


class IGTParseException(Exception):
	def __init__(self, msg=''): 
		super(Exception)
	
class IGTGlossLangLengthException(IGTParseException):
	
	def __init__(self, msg=''):
		super(IGTParseException)

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
	
	@classmethod
	def from_text(cls, textfile, **kwargs):
		# Create a new corpus
		corpus = cls()
		
		# Open the textfile, and read the contents.
		f = open(textfile, 'r', encoding='utf-8')
		data = f.read()
		f.close()
		
		# Find all the text lines
		inst_txts = re.findall('doc_id=[\s\S]+?\n\n', data)
		for inst_txt in inst_txts:
			try:
				i = IGTInstance.from_string(inst_txt, **kwargs)
				corpus.append(i)
			except IGTParseException as e:
				pass
			
		return corpus
		
	
#===============================================================================
# IGT Instance Class
#===============================================================================
		
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
	
	#===========================================================================
	# Convert Instance to XIGT
	#===========================================================================
	
	def to_xigt(self):
		
		# Initialize new IGT instance...
		xi = xigt.Igt()
		for tier in [self.lang(), self.gloss(), self.trans()]:
			xi.add(tier.to_xigt())
	
	@classmethod
	def from_lines(cls, l, g, t, **kwargs):
		
		instid = kwargs.get('id', None)
		inst = cls(id = instid)
		
		if kwargs.get('merge', True):
			lang_line = merge_lines(l)
			gloss_line = merge_lines(g)
			trans_line = merge_lines(t)
		else:
			lang_line = l[0] if l else ''
			gloss_line = g[0] if g else ''
			trans_line = t[0] if t else ''
			
		#=======================================================================
		# Raise an exception if corruption
		#=======================================================================
		if kwargs.get('corruption_exception', False):
			if len(l) > 2 or len(g) > 2 or len(t) > 2:
				raise IGTParseException
			
		lang_line = clean_lang_string(lang_line.lower())
		gloss_line = clean_gloss_string(gloss_line.lower())
		trans_line = clean_trans_string(trans_line.lower())
		
		#=======================================================================
		# Make sure that the gloss and language line align
		#=======================================================================
		lang_t = IGTTier.fromString(lang_line, kind='lang')
		gloss_t = IGTTier.fromString(gloss_line, kind='gloss')
		trans_t = IGTTier.fromString(trans_line, kind='trans')
		
		# If the gloss line has more tokens, see if
		# any are unhyphenated infinitives (e.g. to-visit)
		if len(gloss_t) > len(lang_t) and kwargs.get('infinitive_repair', True):
			gloss_line = hyphenate_infinitive(gloss_line)
			gloss_t = IGTTier.fromString(gloss_line, kind='gloss')
		
		# Raise an exception if, after everything, 
		# the lang and gloss lines do not have the
		# same number of tokens.
		if len(lang_t) != len(gloss_t):			
			raise IGTGlossLangLengthException('%s\n%s\n%s\n' % (lang_line, gloss_line, trans_line))
		
		inst.append(lang_t)
		inst.append(gloss_t)
		inst.append(trans_t)
		return inst
		
	
	@classmethod
	def from_string(cls, string, **kwargs):
		'''
		Method to parse and create an IGT instance from text.
		
		@param cls:
		@param string:
		'''
		# Start by looking for the doc_id
		txtid = re.search('doc_id=([0-9\s]+)', string).group(1)
		inst = cls(id = txtid)
		
		# Now, find all the lines
		lines = re.findall('line=([0-9]+)\stag=(\S+):(.*)\n', string)
		
		# Merge all the lang lines into one
		l = [line[2] for line in lines if 'L' in line[1]]				
		g = [line[2] for line in lines if 'G' in line[1]]
		t = [line[2] for line in lines if 'T' in line[1]]
		
		return cls.from_lines(l,g,t,**kwargs)
		
		
		
		
	def lang_line_classifications(self, classifier, **kwargs):
		
		token_sequence = []
		
		for i, gloss_token in enumerate(self.gloss):
			gloss_token = GoldTagPOSToken.fromToken(gloss_token, goldlabel='NONE')
			#print(gloss_token)
			sio = StringIO()
			write_gram(gloss_token, type='classifier', output=sio, **kwargs)
			
			c_token = sio.getvalue().strip()
			sio.close()
						
			result = classifier.classify(c_token)
			best=result.largest()
			
			#===================================================================
			# Assign the classified gloss tokens to the language tokens.
			#===================================================================
			lang_token = self.lang[i]
			pos = best[0]
			c_token = POSToken(lang_token.seq, label=pos, index=i+1)
			token_sequence.append(c_token)
			
			#===================================================================
			
		return token_sequence
	
			
	def text(self):
		return '%s\n%s\n%s' % (self.lang_texts(), self.gloss_texts(), self.trans_texts())
			
		
	def gloss_alignments(self):
		print(self.id)
		a = AlignedSent(self.gloss, self.trans, self.glossalign)
		a.attrs = self.attrs
		return a
	
	def lang_to_trans_align(self):
		'''
		Given the alignment of lang to gloss and
		gloss to trans, return the alignment of
		lang to trans.
		'''
		new_align = []
		
		# For each lang_index, gloss_index in the 
		# lang alignment, find what tran_indexes
		# the gloss index is aligned to, and 
		# pair those with the lang_index.
		for l_i, g_i in self.langalign:
			t_is = self.glossalign.src_to_tgt(g_i)
			for t_i in t_is:
				# Remember, a zero index means "NULL"
				if t_i > 0:
					new_align.append((l_i, t_i))
				
		# Now return our new alignment.
		return Alignment(new_align)
	
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
		
	def lang_texts(self, **kwargs):
		return self.lang.text(**kwargs)
		
	def gloss_texts(self, **kwargs):
		return self.gloss.text(**kwargs)	
	
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
	
	def lang_gold_alignment(self, **kwargs):
		ga = self.glossalign
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
			
		# If we DO have an alignment between language line
		# and translation line...
		else:
			return AlignedSent(self.lang, self.trans, la)
	
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
		
		for token in tokenize_string(string, tokenizer=whitespace_tokenizer):
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
	

	
	
		

		
	
		
#===============================================================================
# Unit tests
#===============================================================================
		
class MorphTestCase(unittest.TestCase):

	def runTest(self):
		m1 = Morph('the')
		m2 = Morph('dog')
		m3 = Morph('the')
		
		self.assertTrue(m1.morphequals(m3))
		self.assertFalse(m2.morphequals(m1))
		
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
		