'''
Created on Mar 21, 2014

@author: rgeorgi
'''
from _collections import defaultdict

class StatDict(defaultdict):
	'''
	classdocs
	'''

	def __init__(self, type=int):
		'''
		Constructor
		'''
		defaultdict.__init__(self, type)
		
	@property
	def total(self):
		return sum(self.values())
	
	@property
	def distribution(self):
		return {(k,float(v)/self.total) for k, v in self.items()}
	
	@property
	def counts(self):
		return set(self.items())