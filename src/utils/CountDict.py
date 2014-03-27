'''
Created on Aug 26, 2013

@author: rgeorgi
'''
import sys
from _collections import defaultdict
from _functools import reduce

class CountDict(defaultdict):
	def __init__(self):
		defaultdict.__init__(self, int)
		
	def add(self, key, value=1):
		if key not in self.dict:
			self.dict[key] = value
		else:
			self.dict[key] += value

	def keys(self):
		return dict.keys(self)
	
	def __str__(self):
		return str(self.dict)
	def __repr__(self):
		return str(self)
	
	def total(self):
		values = self.dict.values()
		return reduce(lambda x, y: x+y, values)
			
	
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
			