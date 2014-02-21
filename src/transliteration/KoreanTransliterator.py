'''
Created on Jan 31, 2014

@author: rgeorgi
'''
import Transliterator
import codecs
from hangul import translit
import sys

class KoreanTransliterator:
	'''
	classdocs
	'''


	def __init__(self):
		'''
		Constructor
		'''
		pass
		
	def translit(self, string):
		kor = translit.romanize(string)
		kor = codecs.encode(kor, 'ascii', 'replace')
		return kor
		
		
	def yale(self, char):
		d = {'\u314F':'a', # VOWELS:
			'\u3150':'ay',
		 	'\u3151':'ya',
		 	'\u3152':'yay',
		 	'\u3153':'e',
		 	'\u3154':'ey',
		 	'\u3155':'ye',
		 	'\u3156':'yey',
		 	'\u3157':'o',
		 	'\u3158':'wa',
		 	'\u3159':'way',
		 	'\u315a':'oy',
		 	'\u315b':'yo',
		 	'\u315c':'u',
		 	'\u315d':'we',
		 	'\u315e':'wey',
		 	'\u315f':'wi',
		 	'\u3160':'yu',
		 	'\u3161':'u',
		 	'\u3162':'uy',
		 	'\u3163':'i',
		 	'\u3131':'k', # CONSONANTS
		 	'\u3132':'kk',
		 	'\u3134':'n',
		 	'\u3137':'t',
		 	'\u3138':'tt',
		 	'\u3139':'l',
		 	'\u3141':'m',
		 	'\u3142':'p',
		 	'\u3143':'pp',
		 	'\u3145':'s',
		 	'\u3146':'ss',
		 	'\u3147':'ng',
		 	'\u3148':'c',
		 	'\u3149':'cc',
		 	'\u314a':'ch',
		 	'\u314b':'kh',
		 	'\u314c':'th',
		 	'\u314d':'ph',
		 	'\u314e':'h'		 	
		}
		
		if char in d:
			return d[char]
		else:
			return char
		
if __name__ == '__main__':
	f = codecs.open('/Users/rgeorgi/ownCloud/treebanks/universal_treebanks_v1.0/ko/ko-universal-train.conll', 'r', 'utf-8')
	kt = KoreanTransliterator()
	for line in f:
		print kt.translit(line)