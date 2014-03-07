'''
Created on Mar 7, 2014

@author: rgeorgi
'''
from alignment.Alignment import Alignment

class IGTCorpus(list):
	'''
	Object that will hold a corpus of IGT instances.
	'''
	
	def __init__(self, seq = []):
		list.__init__(self, seq)
		
		
class IGTInstance(list):
	'''
	Container class for an IGT instance and all the dealings that will go on inside it.
	'''
	
	def __init__(self, seq=[], id = None):		
		self._id = id
		self.glossalign = Alignment()
		self.langalign = Alignment()
		list.__init__(self, seq)
		
	def append(self, item):
		if not isinstance(item, IGTTier):
			raise IGTException('Attempt to append a non-IGTTier instance to an IGTInstance')
		list.append(self, item)
		
	def gloss(self):
		return [tier for tier in self if tier.kind == 'gloss']
	
	def trans(self):
		return [tier for tier in self if tier.kind == 'trans']
	
	def lang(self):
		return [tier for tier in self if tier.kind == 'lang']
	
	def __str__(self):
		ret_str = ''
		for kind in set([tier.kind for tier in self]):
			ret_str += '%s,'%str(kind)
		return '<IGTInstance %d: %s>' % (self._id, ret_str[:-1]) 
		
		
class IGTException(Exception):
	def __init__(self, m = ''):
		Exception.__init__(self, m)
		
class IGTTier(list):
	'''
	Class to hold individual tiers of IGT instances.
	'''
	
	def __init__(self, seq=[], kind = None):
		self.kind = kind
		list.__init__(self, seq)
		
	def append(self, item):
		if not isinstance(item, IGTToken):
			raise IGTException('Attempt to add non-IGTToken to IGTTier')
		else:
			list.append(self, item)
			
	def __str__(self):
		return '<IGTTier kind=%s len=%d>' % (self.kind, len(self))
		
class IGTToken(str):
	
	def __init__(self, seq=''):
		str.__init__(self, seq)
		