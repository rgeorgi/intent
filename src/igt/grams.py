'''
Created on Mar 8, 2014

@author: rgeorgi
'''

gramdict = {'1sg':'i',
		'det':['the'],
		'3pl':['they'],
		'3sg':['he','she', 'him', 'her'],
		'2sg':['you'],
		'2pl':['you']}

def sub_grams(gram):
	if gram in gramdict:
		return gramdict[gram]
	else:
		return [gram]
	