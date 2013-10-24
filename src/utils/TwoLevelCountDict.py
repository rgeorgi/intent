'''
Created on Oct 24, 2013

@author: rgeorgi
'''
from CountDict import CountDict


class TwoLevelCountDict():
	def __init__(self):
		self.dict = {}
	def add(self, key_a, key_b, value=1):
		if key_a not in self.dict:
			newdict = CountDict()
			newdict.add(key_b, value)
			self.dict[key_a] = newdict
		else:
			self.dict[key_a].add(key_b, value)
			
	def keys(self):
		return self.dict.keys()
	def __contains__(self, key):
		return key in self.dict
	def __getitem__(self, key):
		return self.dict[key]
	
	def __str__(self):
		return str(self.dict)
	
	def most_frequent(self, key):
		return self[key].most_frequent()
	
	