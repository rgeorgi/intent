'''
Created on Mar 8, 2014

@author: rgeorgi
'''

gramdict = {'1sg':['i','me'],
		'det':['the'],
		'3pl':['they'],
		'3sg':['he','she', 'him', 'her'],
		'3sgf':['she','her'],
		'2sg':['you'],
		'3sgp':['he'],
		'poss':['his','her','my', 'their'],
		'neg':["n't",'not'],
		'2pl':['you']}

def sub_grams(gram):
	if gram in gramdict:
		return gramdict[gram]
	else:
		return [gram]
	