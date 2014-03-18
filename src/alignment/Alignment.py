'''
Created on Feb 21, 2014

@author: rgeorgi
'''

import collections
import sys
import re

class AlignedSent():
	def __init__(self, src_tokens, tgt_tokens, aln):
		self.src_tokens = src_tokens
		self.tgt_tokens = tgt_tokens
		self.aln = aln
		self.attrs = {}
		
		if type(aln) != Alignment:
			raise AlignmentError('Passed alignment is not of type Alignment')
		
		for a in self.aln:
			src_i, tgt_i = a
			if src_i - 1 >= len(self.src_tokens):
				raise AlignmentError('Source index %d is too high for %s'  % (src_i, self.src_tokens))
			if tgt_i - 1 >= len(self.tgt_tokens):
				raise AlignmentError('Target index %d is too high for sentence %s' % (tgt_i, self.tgt_tokens))	
			
	def aligned_words(self):
		words = set([])
		for src_i, tgt_i in self.aln:
			words.add((self.src_tokens[src_i-1], self.tgt_tokens[tgt_i-1]))
		return words
			
	def flipped(self):
		new_align = map(lambda aln: (aln[1], aln[0]), self.aln)
		return AlignedSent(self.tgt_tokens, self.src_tokens, Alignment(new_align))
			
	def pairs(self, src=None, tgt=None):
		return [aln for aln in self.aln if (src and src==aln[0]) or (tgt and tgt==aln[1]) ]
			
	def wordpairs(self, ips=None):
		'''
		Return the pairs of words referred to by the indices in ips.
		
		This is either an aribitrary pair of indices passed as an argument,
		or the indices contained in the alignment property.
		@param ips:
		'''
		if ips is None:
			ips = self.aln
		return [self.wordpair(ip) for ip in ips]
	
				
	def wordpair(self, ip):
		'''
		Return the wordpair corresponding with an alignment pair.
		@param ip:
		'''
		return(self.src_tokens[ip[0]-1], self.tgt_tokens[ip[1]-1])
		
	def __str__(self):
		return '<%s, %s, %s>' % (self.src_tokens, self.tgt_tokens, self.aln)
	
	@property
	def src_text(self):
		return ' '.join(self.src_tokens)
	
	@property
	def tgt_text(self):
		return ' '.join(self.tgt_tokens)
	
	def set_attr(self, key, val):
		self.attrs[key] = val
		
	def get_attr(self, key):
		return self.attrs[key]
	
	@property
	def srclen(self):
		return len(self.src_tokens)
	
	@property
	def tgtlen(self):
		return len(self.tgt_tokens)
		
		
class AlignedCorpus(list):
	def __init__(self):
		super(AlignedCorpus).__init__(AlignedCorpus)
		
	def write(self, src_path, tgt_path, aln_path):
		src_f = open(src_path, 'w')
		tgt_f = open(tgt_path, 'w')
		aln_f = open(aln_path, 'w')
		
		for a_sent in self:
			
			src = a_sent.src_text()
			tgt = a_sent.tgt_text()
			aln = str(a_sent.aln)
			
			src_f.write(src+'\n')
			tgt_f.write(tgt+'\n')
			aln_f.write(aln+'\n')
		
		src_f.close(), tgt_f.close(), aln_f.close()
		
	def read(self, src_path, tgt_path, aln_path, limit=None):
		'''
		Read in the morph:gloss:aln alignment format
		
		@param src_path: Source sents
		@param tgt_path: Target sents
		@param aln_path: Alignment filename
		@param limit: Sentence limit
		'''
		src_f = open(src_path, 'r')
		tgt_f = open(tgt_path, 'r')
		aln_f = open(aln_path, 'r')
		
				
		src_lines = src_f.readlines()
		tgt_lines = tgt_f.readlines()
		aln_lines = aln_f.readlines()
		
		src_f.close(), tgt_f.close(), aln_f.close()
		
		lines = zip(src_lines, tgt_lines, aln_lines)
		i = 0
		for src_line, tgt_line, aln_line in lines:
			src_tokens = src_line.split()
			tgt_tokens = tgt_line.split()
			
			alignments = []
			#===================================================================
			# Read the aligment data
			#
			# The gloss-with-morph data will be read in "morph:gloss:aln" format.
			#===================================================================			
			aln_tokens = aln_line.split()
			
			
			for aln_token in aln_tokens:
				src_index, aln_indices = aln_token.split(':')
				aln_indices = [int(aln) for aln in aln_indices.split(',') if aln.strip()]
								
				
				for aln_index in aln_indices:
					alignments.append((int(src_index), aln_index))									
			
			a_sent = AlignedSent(src_tokens, tgt_tokens, Alignment(alignments))
			self.append(a_sent)
			
			i+= 1
			if limit and i == limit:
				break
			

			
	def read_giza(self, src_path, tgt_path, a3, limit=None):
		'''
		Method intended to read a giza A3.final file into an alignment format.
		
		@param src_path: path to the source sentences
		@param tgt_path: path to the target sentences
		@param a3: path to the giza A3.final file.
		@param limit: 
		'''
		src_f = open(src_path, 'r')
		tgt_f = open(tgt_path, 'r')
		aln_f = open(a3, 'r')
		
		src_lines = src_f.readlines()
		tgt_lines = tgt_f.readlines()
		aln_lines = aln_f.read()
		
		src_f.close, tgt_f.close(), aln_f.close()
		
		alignments = []
		
		#------------------------------------------------------------------------------
		# Do all the parsing of the A3.final file.
		 
		alns = re.findall('NULL.*', aln_lines, flags=re.M)
		for aln in alns:
			alignment = Alignment()
			elts = re.findall('\(\{([0-9\s]+)\}\)', aln)
			
			# Starting from 1 means we skip the NULL alignments.
			for i in range(0,len(elts)):
				elt = elts[i]
				indices = map(lambda ind: int(ind), elt.split())
				for index in indices:
					alignment.add((i, index))
			alignments.append(alignment)
			
		#------------------------------------------------------------------------------
		# now, back to creating the corpus
		lines = zip(src_lines, tgt_lines, alignments)
		i = 0
		for src_line, tgt_line, aln in lines:
			a_sent = AlignedSent(src_line.split(), tgt_line.split(), aln)
			a_sent.attrs['file'] = a3
			a_sent.attrs['id'] = None
			self.append(a_sent)
			i+=1
			if limit and i == limit:
				break
			
			
#===============================================================================
# Combine AlignedSents
#===============================================================================

def union(a1, a2):
	return a1 | a2

def combine_corpora(a1, a2, method='intersect'):
	
	# Do some error checking
	if not isinstance(a1, AlignedCorpus) or not isinstance(a2, AlignedCorpus):
		raise AlignmentError('Attempt to intersect non-aligned corpus')
	elif len(a1) != len(a2):
		raise AlignmentError('Length of aligned corpora are mismatched')
	
	i_ac = AlignedCorpus()
	
	for a1_sent, a2_sent in zip(a1, a2):
		i_snt = combine_sents(a1_sent, a2_sent, method=method)
		i_ac.append(i_snt)
	return i_ac
	
	
def combine_sents(s1, s2, method='intersect'):
	if not isinstance(s1, AlignedSent) or not isinstance(s2, AlignedSent):
		raise AlignmentError('Attempt to intersect non-AlignedSents')
	elif s1.srclen != s2.tgtlen:
		raise AlignmentError('Length of sources do not match')
	elif s1.tgtlen != s2.srclen:
		raise AlignmentError('Length of targets do not match')
	
	if method == 'intersect':
		# Actually take the intersection
		return AlignedSent(s1.src_tokens, s1.tgt_tokens, s1.aln & s2.aln.flip())
	elif method == 'union':
		return AlignedSent(s1.src_tokens, s1.tgt_tokens, s1.aln | s2.aln.flip())
	elif method == 'refined':
		return refined_combine(s1, s2)
	else:
		raise AlignmentError('Unknown combining method')
	
def refined_combine(s1, s2):
	A_1 = s1.aln
	A_2 = s2.aln.flip()
	
	A = A_1 & A_2
	
	remaining = (A_1 | A_2) - A
	while remaining:
		i, j = remaining.pop()
		
		# ...if neither f_j or e_i has an alignment in A..
		if not(A.contains_src(i) or A.contains_tgt(j)):
			A.add((i,j))
			continue
			
		# ...or if:
		#
		#  1) The alignment (i, j) has a horizontal neighbor
		#     (i-1, j), (1+1, j) or a vertical neighbor
		#     (i, j-1), (i,j+1) that is already in A
		#
		#  2) The set A | {(i,j)} does not contain alignments
		#     with BOTH horizontal and vertical neighbors.
		horizontal = {(i-1,j),(i+1,j)} & A
		vertical = {(i,j-1),(i,j+1)} & A
		
		if horizontal and vertical:
			continue
		else:
			A.add((i,j))
			
		
	return AlignedSent(s1.src_tokens, s1.tgt_tokens, A)
	
	
	
	
	

class AlignmentError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

#===============================================================================
# Alignment Class
#===============================================================================

class Alignment(set):
	'''
	Simply, a set of (src_index, tgt_index) pairs in a set.
	'''
	
	def __init__(self, iter=[]):
		super(Alignment).__init__(Alignment)
		for i in iter:
			self.add(i)
		
	def __str__(self):
		ret_str = ''
		for elt in self:
			ret_str += str(elt)+', '
		return ret_str[:-2]
		
	def contains_tgt(self, key):
		contains = False
		for pair in self:
			src, tgt = pair
			if tgt == key:
				return pair
		return contains
	
	def contains_src(self, key):
		contains = False
		for pair in self:
			src, tgt = pair
			if src == key:
				return pair
		return contains 
	
	def __sub__(self, o):
		return Alignment(set.__sub__(self, o))
	
	def __or__(self, o):
		return Alignment(set.__or__(self, o))
	
	def __and__(self, o):
		return Alignment(set.__and__(self, o))
	
	def flip(self):
		a = Alignment()
		for pair in self:
			a.add((pair[1], pair[0]))
		return a
		