'''
Created on Oct 24, 2013

@author: rgeorgi
'''
from utils.CountDict import CountDict
from collections import defaultdict
import re
import pickle
import sys
from functools import partial


class TwoLevelCountDict(object):
	def __init__(self):
		self._dict = defaultdict(CountDict)
		
	def add(self, key_a, key_b, value=1):
		self[key_a][key_b] += value
			
	def top_n(self, key, n=1, min_num = 1, key2_re = None):
		s = sorted(self[key].items(), reverse=True, key=lambda x: x[1])
		if key2_re:
			s = [i for i in s if re.search(key2_re, i[0])]
			
		return s[0:n]

	def most_frequent(self, key, num = 1, key2_re = None):
		most_frequent = None
		biggest_count = 0
		for key2 in self[key]:
			if not re.search(key2_re, key2):
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
	
	#===========================================================================
	# Stuff that should've been inherited
	#===========================================================================
	
	def __str__(self):
		return self._dict.__str__()
	
	def __getitem__(self, k):
		return self._dict.__getitem__(k)
	
	def __setitem__(self, k, v):
		self._dict.__setitem__(k, v)
		
	def __contains__(self, k):
		return self._dict.__contains__(k)
		
	def keys(self):
		return self._dict.keys()
	
	def __len__(self):
		return self._dict.__len__()
	
	
	
	