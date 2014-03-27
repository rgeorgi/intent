'''
Created on Mar 8, 2014

@author: rgeorgi
'''

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem.snowball import EnglishStemmer
from nltk.stem.porter import PorterStemmer
import re
import unittest
from corpora.POSCorpus import POSToken
from utils.Token import Token



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
	for match in re.finditer('\S+', st, re.UNICODE):
		yield Token(match.group(0), span=Span((match.start(), match.end())))

def morpheme_tokenizer(st):
	for match in re.finditer('[^\s\-\.:/\(\)]+', st):
		yield Token(match.group(0), span=Span((match.start(), match.end())))

def tag_tokenizer(st):
	for match in re.finditer('(\S+)/(\S+)', st, re.UNICODE):
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

class Tokenization(list):
	'''
	Container class for a tokenization.
	'''
	def __init__(self, seq=[], original=''):
		self.original = original
		list.__init__(self, seq)	



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
		
		
	