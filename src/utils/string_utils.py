'''
Created on Mar 8, 2014

@author: rgeorgi
'''

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem.snowball import EnglishStemmer

global s
# s = WordNetLemmatizer()
s = EnglishStemmer()

def stem_token(st):
	return s.stem(st)
# 	return s.lemmatize(st)