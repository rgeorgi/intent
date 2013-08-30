'''
Created on Aug 26, 2013

@author: rgeorgi
'''

class CountDict():
	def __init__(self):
		self.dict = {}
	def add(self, key, value=1):
		if key not in self.dict:
			self.dict[key] = value
		else:
			self.dict[key] += value
	def __contains__(self, key):
		return key in self.dict
	def __getitem__(self, key):
		return self.dict[key]
	def keys(self):
		return self.dict.keys()
	
	def __str__(self):
		return str(self.dict)
	def __repr__(self):
		return str(self)