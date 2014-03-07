'''
Created on Oct 24, 2013

@author: rgeorgi
'''
from utils.CountDict import CountDict
from collections import defaultdict


class TwoLevelCountDict(defaultdict):
	def __init__(self):
		defaultdict.__init__(self, lambda: CountDict())
		
	def add(self, key_a, key_b, value=1):
		self[key_a][key_b] += value
			

	def most_frequent(self, key, num = 1):
		most_frequent = None
		biggest_count = 0
		for key2 in self[key]:
			count = self[key][key2]
			if count > biggest_count and count >= num:
				most_frequent = key2
				biggest_count = count
				
		return most_frequent
	
	def total(self, key):
		count = 0
		for key2 in self[key]:
			count += self[key][key2]
		return count
			
	
	def distribution(self, key):
		dist_set = set([])
		
		total = 0
		for key2 in self[key].keys():
			total += self[key][key2]
		
		for key2 in self[key]:
			dist_set.add((key2, self[key][key2] / float(total)))
			
		return dist_set
	
	