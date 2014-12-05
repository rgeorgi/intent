'''
Created on Mar 21, 2014

@author: rgeorgi
'''
from utils.string_utils import string_compare_with_processing
import re
from xigt.core import Item
from collections import OrderedDict

#===============================================================================
# Main Token Class
#===============================================================================

class Token(Item):

	def __init__(self, content, **kwargs):
		
		# Essentially manually override the xigt
		# constructor.		
		self.id = kwargs.get('id')
		self.type = kwargs.get('type')
		self.attributes = kwargs.get('attributes') or OrderedDict()
		self._content = content
		self._parent = kwargs.get('tier')

		# Add span info		
		if 'span' in kwargs:
			self.attributes['span'] = kwargs.get('span')
		
		# Add index info
		if 'index' in kwargs:
			self.attributes['index'] = kwargs.get('index')	
		

	def __str__(self):
		return '<%s %s>' % (self.__class__.__name__, self.content)
	
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
		return self.attributes
		
	@attrs.getter
	def attrs(self):
		return self.attributes
	
	@property
	def seq(self):
		return self.content
	
	@property
	def index(self):
		return self.attributes.get('index')
	
	@index.setter
	def index(self, value):
		self.attributes['index'] = value
		
	def __eq__(self, o):
		return o.seq == self.seq and self.index == o.index
		
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
	def __init__(self, content, **kwargs):
		Token.__init__(self, content, **kwargs)
		if 'label' in kwargs:
			self.label = kwargs.get('label')
			
		
		
		
	@property
	def label(self):
		return self.attributes.get('label')
	
	@label.setter
	def label(self, v):
		if v:
			self.attributes['label'] = v
	
	
	@classmethod
	def fromToken(cls, t, **kwargs):
		return cls(t.seq, **kwargs)
		
		
class GoldTagPOSToken(Token):
	def __init__(self, content, **kwargs):
		Token.__init__(self, content, **kwargs)
		self.taglabel = kwargs.get('taglabel')
		self.goldlabel = kwargs.get('goldlabel')
		
	@classmethod
	def fromToken(cls, t, taglabel = None, goldlabel = None):
		return cls(t.seq, taglabel=taglabel, goldlabel=goldlabel, span=t.span, index=t.index, parent=t.parent)
	
	@property
	def taglabel(self):
		return self.attributes.get('taglabel')
	
	@taglabel.setter
	def taglabel(self, v):
		self.attributes['taglabel'] = v
	
	@property	
	def goldlabel(self):
		return self.attributes.get('goldlabel')
	
	@goldlabel.setter
	def goldlabel(self, v):
		self.attributes['goldlabel'] = v

		
#===============================================================================
# Morph
#===============================================================================
		
class Morph(Token):
	'''
	This class is what makes up an IGTToken. Should be comparable to a token
	'''
	def __init__(self, seq='', span=None, parent=None):
		index = parent.index if parent else None
		Token.__init__(self, content=seq, span=span, index=index, tier=parent)
		
		
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
		yield Token(match.group(0), span=Span((match.start(), match.end())))

def morpheme_tokenizer(st):
	pieces = re.split('[\s\-\.:/\(\)=]+', st)
	matches = [p for p in pieces if p.strip()]

	for match in matches:
		yield Token(match)

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
		
	def text(self):
		return ' '.join([t.seq for t in self])

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