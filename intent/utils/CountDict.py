'''
Created on Aug 26, 2013

@author: rgeorgi
'''
import sys
from _collections import defaultdict
from _functools import reduce

class CountDict(object):
	def __init__(self):
		self._dict = defaultdict(int)		
		
	def add(self, key, value=1):
		self[key] += value
	
	def __str__(self):
		return self._dict.__str__()
	
	def __repr__(self):
		return self._dict.__repr__()
	
	def total(self):
		values = self._dict.values()
		total = 0
		for v in values:
			total += v
		return total
			
	#===========================================================================
	#  Stuff that should be inheritable
	#===========================================================================
			
	def __getitem__(self, k):
		return self._dict.__getitem__(k)
	
	def __setitem__(self, k, v):
		self._dict.__setitem__(k, v)
	
	def __contains__(self, k):
		return self._dict.__contains__(k)
		
	def __len__(self):
		return self._dict.__len__()
		
	def __delitem__(self, k):
		self._dict.__delitem__(k)
		
	def keys(self):
		return self._dict.keys()
	
	def items(self):
		return self._dict.items()
	
	#  -----------------------------------------------------------------------------
			
	def largest(self):
		return sorted(self.items(), reverse=True, key=lambda k: k[1])[0]
	
	def most_frequent(self, minimum = 0, num = 1):
		'''
		Return the @num entries with the highest counts that
		also have at least @minimum occurrences. 
		
		@param minimum: int
		@param num: int
		'''
		items = list(self.items())
		items.sort(key = lambda item: item[1], reverse=True)
		ret_items = []
		for item in items:
			if item[1] > minimum:
				ret_items.append(item[0])
			if num and len(ret_items) == num:
				break
		
		return ret_items
	
	def most_frequent_count(self, minimum = 0, num = 1):
		most_frequent_keys = self.most_frequent(minimum, num)
		most_frequent_values = map(lambda key: self[key], most_frequent_keys)
		return most_frequent_values
			