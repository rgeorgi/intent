'''
Created on Mar 8, 2014

@author: rgeorgi
'''

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem.snowball import EnglishStemmer
from nltk.stem.porter import PorterStemmer
import igt




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


		
def string_compare_with_processing(s1, s2, **kwargs):
	'''
	Given two strings, do all the various processing tricks to decide if they match or not.
	
	@param s1: First string to compare
	@param s2: Second string to compare
	'''
	
	# Before we do anything, see if we have a match.
	if s1 == s2:
		return True
	
	if kwargs.get('lowercase', True):
		s1 = s1.lower()
		s2 = s2.lower()
		
	# Keep checking...
	if s1 == s2:
		return True
		
		
	# Do various types of increasingly aggressive stemming...
	if kwargs.get('stem', True):
		stem1 = lemmatize_token(s1)
		stem2 = lemmatize_token(s2)
		
		if stem1 == stem2:
			return True

		stem1 = stem_token(s1)
		stem2 = stem_token(s2)
			
		if stem1 == stem2:
			return True
		
		stem1 = lemmatize_token(s1, 'a')
		stem2 = lemmatize_token(s2, 'a')
			
		if stem1 == stem2:
			return True
	
		stem1 = lemmatize_token(s1, 'n')
		stem2 = lemmatize_token(s2, 'n')
		
		if stem1 == stem2:
			return True
	
	# We could do the gram stuff here, but it doesn't work too well.
	# Instead, let's try doing it as a second pass to pick up stil-unaligned
	# words.
	if kwargs.get('gloss_on',False):
		gloss_grams_1 = igt.grams.sub_grams(s1)
		gloss_grams_2 = igt.grams.sub_grams(s2)
		
		if s2.strip() and s2 in gloss_grams_1:
			return True
		if s1.strip() and s1 in gloss_grams_2:
			return True
					
		
		
	return s1 == s2
		
	