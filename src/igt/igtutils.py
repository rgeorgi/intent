'''
Created on Mar 11, 2014

@author: rgeorgi
'''

import re

def clean_gloss_string(string):
	return re.sub('^\s*(?:\([^\)]+\))', string)