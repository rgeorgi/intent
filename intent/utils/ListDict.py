'''
Created on Aug 30, 2013

@author: rgeorgi
'''
class ListDict:
	
	def __init__(self):
		self._dict = {}
		
	def __contains__(self, k):
		return k in self._dict.keys()
		
	def add(self, key, value):
		if key not in self._dict:
			self._dict[key] = [value]
		else:
			self._dict[key] += [value]
			
	def copy(self):
		new = ListDict()
		for key in self.keys():
			for li in self[key]:
				new.add(key, li)
		return new
	
	def remove_value(self, key, value):
		if key in self and value in self[key]:
			self[key].remove(value)
	
	def remove_key(self, key):
		if key in self:
			del self[key]
	
	def __iter__(self):
		return self._dict.__iter__()
			
	def __delitem__(self, key):
		del self._dict[key]
			
	def __getitem__(self, key):
		return self._dict[key]
	
	def __len__(self):
		return len(self._dict)
	
	def __str__(self):
		return str(self._dict)
	
	def keys(self):
		return self._dict.keys()
	
	def values(self):
		vals = []
		for key in self.keys():
			vals += self._dict[key]
		return vals

		