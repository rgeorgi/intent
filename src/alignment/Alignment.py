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
				raise AlignmentError('Target index %d is too high' % tgt_i)			
			
	def aligned_words(self):
		words = set([])
		for src_i, tgt_i in self.aln:
			words.add((self.src_tokens[src_i-1], self.tgt_tokens[tgt_i-1]))
		return words
			
	def flipped(self):
		new_align = map(lambda aln: (aln[1], aln[0]), self.aln)
		return AlignedSent(self.tgt_tokens, self.src_tokens, Alignment(new_align))
			
	def wordpairs(self, ips):
		return [self.wordpair(ip) for ip in ips]
			
	def wordpair(self, ip):
		'''
		Return the wordpair corresponding with an alignment pair.
		@param ip:
		'''
		return(self.src_tokens[ip[0]-1], self.tgt_tokens[ip[1]-1])
		
	def __str__(self):
		return '<%s, %s, %s>' % (self.src_tokens, self.tgt_tokens, self.aln)
	
	def src_text(self):
		return ' '.join(self.src_tokens)
	
	def tgt_text(self):
		return ' '.join(self.tgt_tokens)
	
	def set_attr(self, key, val):
		self.attrs[key] = val
		
	def get_attr(self, key):
		return self.attrs[key]
		
		
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
			alignments = eval('['+aln_line+']')
			a_sent = AlignedSent(src_tokens, tgt_tokens, Alignment(alignments))
			self.append(a_sent)
			i+= 1
			if limit and i == limit:
				break
			
	def read_giza(self, src_path, tgt_path, a3, limit=None):
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
			elts = re.findall('\(\{([^\)]+)\}\)', aln)
			for i in range(len(elts)):
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
			self.append(a_sent)
			i+=1
			if limit and i == limit:
				break
			
			
		


class AlignmentError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Alignment(set):
	
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
	
	def flip(self):
		a = Alignment()
		for pair in self:
			a.add((pair[1], pair[0]))
		return a
		