'''
Created on Mar 21, 2014

@author: rgeorgi
'''
from utils.string_utils import string_compare_with_processing
import re

#===============================================================================
# Main Token Class
#===============================================================================

class Token(object):

	def __init__(self, seq='', span=None, index=None, parent=None):
		self.span = span
		self._seq = seq
		self._index = index
		self.parent = parent
		self._attrs = {}

	def __str__(self):
		return '<%s %s>' % (self.seq, self.span)
	
	def __repr__(self):
		return str(self)
	
	@property
	def parent(self):
		return self._parent
	
	@parent.setter
	def parent(self, v):
		self._parent = v
	
	@property
	def attrs(self):
		return self._attrs
		
	@attrs.getter
	def attrs(self):
		return self._attrs
	
	@property
	def seq(self):
		return self._seq
	
	@property
	def index(self):
		return self._index
	
	@index.getter
	def index(self):
		return self._index
	
	@index.setter
	def index(self, value):
		self._index = value
		
	def __eq__(self, o):
		return isinstance(o, Token) and o.seq == self.seq and self.index == o.index
		
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
		
	def morphequals(self, o, **kwargs):
		if not isinstance(o, Token):
			raise TokenException('Attempt to compare {0} to non-{0}'.format(self.__class__.__name__))
		else:
			return string_compare_with_processing(self.seq, o.seq, **kwargs)
		
#===============================================================================
# POSToken
#===============================================================================

class POSToken(Token):
	def __init__(self, form, label = None, index=None, span=None):				
		self.form = form
		self.label = label
		self.index = index
		Token.__init__(self, form, span, index)
		
#===============================================================================
# Morph
#===============================================================================
		
class Morph(Token):
	'''
	This class is what makes up an IGTToken. Should be comparable to a token
	'''
	def __init__(self, seq='', span=None, parent=None):
		index = parent.index if parent else None
		Token.__init__(self, seq, span, index, parent)
		
		
	@classmethod
	def fromToken(cls, token, parent):
		return cls(token.seq, token.span, parent)
		
	def __str__(self):
		return '<Morph: %s>' % self.seq
		
#===============================================================================
# Tokenization Methods
#===============================================================================
		
def whitespace_tokenizer(st):
	for match in re.finditer('\S+', st, re.UNICODE):
		yield Token(match.group(0), Span((match.start(), match.end())))

def morpheme_tokenizer(st):
	for match in re.finditer('[^\s\-\.:/\(\)]+', st):
		yield Token(match.group(0), span=Span((match.start(), match.end())))

def tag_tokenizer(st, delimeter='/'):
	for match in re.finditer('(\S+){}(\S+)'.format(delimeter), st, re.UNICODE):
		yield POSToken(match.group(1), label=match.group(2), span=Span((match.start(), match.end())))

def tokenize_string(st, tokenizer=whitespace_tokenizer):
	tokens = Tokenization()
	iter = tokenizer(st) 
	
	i = 0
	for token in iter:
		token.index = i+1
		tokens.append(token)
		i+=1
	return tokens

#===============================================================================
# Tokenization helper classes
#===============================================================================

class Tokenization(list):
	'''
	Container class for a tokenization.
	'''
	def __init__(self, seq=[], original=''):
		self.original = original
		list.__init__(self, seq)	

class Span(object):
	'''
	Just return a character span.
	'''
	def __init__(self, tup):
		'''
		Constructor
		'''
		self._start = tup[0]
		self._stop = tup[1]
		
	@property
	def start(self):
		return self._start
	
	@property
	def stop(self):
		return self._stop
	
	def __str__(self):
		return '(%s,%s)' % (self._start, self._stop)
	
	def __repr__(self):
		return str(self)

#===============================================================================
# Exceptions
#===============================================================================

class TokenException(Exception):
	pass