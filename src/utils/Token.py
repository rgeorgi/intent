'''
Created on Mar 21, 2014

@author: rgeorgi
'''
from utils.string_utils import string_compare_with_processing

class TokenException(Exception):
	pass

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
		
	def morphequals(self, o, **kwargs):
		if not isinstance(o, Token):
			raise TokenException('Attempt to compare {0} to non-{0}'.format(self.__class__.__name__))
		else:
			return string_compare_with_processing(self.seq, o.seq, **kwargs)
		
class POSToken(Token):
	def __init__(self, form, label = None, index=None, span=None):				
		self.form = form
		self.label = label
		self.index = index
		Token.__init__(self, form, span, index)