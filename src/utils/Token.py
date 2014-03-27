'''
Created on Mar 21, 2014

@author: rgeorgi
'''

class Token(object):

		
	def __str__(self):
		return '<%s %s>' % (self.seq, self.span)
	
	def __repr__(self):
		return str(self)
	
	@property
	def attrs(self):
		return self._attrs
		
	@attrs.getter
	def attrs(self):
		return self._attrs
	
	@property
	def seq(self):
		return self._seq
	
	@property
	def index(self):
		return self._index
	
	@index.getter
	def index(self):
		return self._index
	
	@index.setter
	def index(self, value):
		self._index = value
	
	def __init__(self, seq='', span=None, index=None):
		self.span = span
		self._seq = seq
		self.index = index
		self._attrs = {}