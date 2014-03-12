'''
Created on Mar 8, 2014

@author: rgeorgi
'''

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem.snowball import EnglishStemmer
from nltk.stem.porter import PorterStemmer
import re
import unittest



global s
l = WordNetLemmatizer()
s = EnglishStemmer()
# s = PorterStemmer()

def stem_token(st):
	return s.stem(st)
# 	return s.stem(st)
# 	return s.lemmatize(st)

def lemmatize_token(st, pos='v'):
	return l.lemmatize(st, pos)

def whitespace_tokenizer(st):
	return re.finditer('\S+', st, re.UNICODE)

def morpheme_tokenizer(st):
	return re.finditer('[^\s\-\.:/\(\)]+', st)


def tokenize_string(st, tokenizer=whitespace_tokenizer):
	tokens = Tokenization()
	iter = tokenizer(st) 
	
	i = 0
	for match in iter:
		s = Span((match.start(), match.end()))
		t = Token(match.group(0), span=Span((match.start(), match.end())), index=i+1)
		tokens.append(t)
		i+=1
	return tokens

class Tokenization(list):
	'''
	Container class for a tokenization.
	'''
	def __init__(self, seq=[], original=''):
		self.original = original
		list.__init__(self, seq)	

class Token(object):

		
	def __str__(self):
		return '<%s %s>' % (self.seq, self.span)
	
	def __repr__(self):
		return str(self)
	
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
	
	def __init__(self, seq='', span=None, index=None):
		self.span = span
		self._seq = seq
		self.index = index
		self._attrs = {}

class Span(tuple):
	'''
	Just return a character span.
	'''
	def __init__(self, tup):
		'''
		Constructor
		'''
		tuple.__init__(self, tup)			
		
	@property
	def start(self):
		return self[0]
	
	@property
	def stop(self):
		return self[1]
	
	
	
class WhitespaceTokenizerTest(unittest.TestCase):
	def runTest(self):
		string = 'This is the test sentence'
		print(tokenize_string(string))
		
		
	