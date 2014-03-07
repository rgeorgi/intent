'''
Created on Mar 6, 2014

@author: rgeorgi
'''
from utils.TwoLevelCountDict import TwoLevelCountDict
import re

class TagCounter:
	'''
	classdocs
	'''


	def __init__(self, path = None, delimeter = '/', lowercase = True, format='splittags'):
		'''
		Constructor
		'''
		if path:
			self._docount(path, delimeter, lowercase, format)
			
		
			
		
	def _docount(self, tagged_path, delimeter = '/', lowercase = True, format='splittags'):
		tp = open(tagged_path, 'r')
	
		#===========================================================================
		# Let's keep a count of all the "features" (words) and their tag distributions.
		#===========================================================================
		
		self.counts = TwoLevelCountDict()
		
		for line in tp:
			if format == 'splittags':
				for token in line.split():
					word, tag = token.split(delimeter)
					
				# Lowercase if necessary
				if lowercase:
					word = word.lower()
				
				self.counts.add(word, tag)
				
			# Mallet format is one word per line
			elif format == 'mallet':
				if not line.strip():
					continue			
				word, tag = re.split('\s+', line.strip())
				self.counts.add(word, tag)
				
	def most_frequent(self, key):
		return self.counts.most_frequent(key)
				
	def total(self, key):
		return self.counts.total(key)
				
	def distribution(self, key):
		return self.counts.distribution(key)
	
	def keys(self):
		return self.counts.keys()
		