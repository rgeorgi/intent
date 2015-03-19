'''
Created on Oct 23, 2013

@author: rgeorgi
'''
from utils.ListDict import ListDict

class SetDict(ListDict):
	def __init__(self):
		ListDict.__init__(self)
	
		
	def copy(self):
		sd = SetDict()
		for key in self.keys():
			for si in self[key]:
				sd.add(key, si)
		return sd
		
	def add(self, key, value):
		if key not in self._dict:
			self._dict[key] = set([value])
		else:
			self._dict[key] |= set([value])