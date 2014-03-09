'''
Created on Mar 8, 2014

@author: rgeorgi
'''

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem.snowball import EnglishStemmer
from nltk.stem.porter import PorterStemmer

global s
l = WordNetLemmatizer()
s = EnglishStemmer()
# s = PorterStemmer()

def stem_token(st):
	return l.lemmatize(s.stem(st), 'v')
# 	return s.lemmatize(st)