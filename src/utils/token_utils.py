'''
Created on Mar 27, 2014

@author: rgeorgi
'''
import re
from utils.Token import Token, POSToken
import unittest
def whitespace_tokenizer(st):
	for match in re.finditer('\S+', st, re.UNICODE):
		yield Token(match.group(0), Span((match.start(), match.end())))

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
	
	
	
class WhitespaceTokenizerTest(unittest.TestCase):
	def runTest(self):
		string = 'This is the test sentence'
		print(tokenize_string(string))