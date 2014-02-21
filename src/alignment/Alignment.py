'''
Created on Feb 21, 2014

@author: rgeorgi
'''

import collections

class Alignment(object):
	'''
	classdocs
	'''


	def __init__(self):
		'''
		Constructor
		'''
		self._map = collections.defaultdict(lambda: -1)
		