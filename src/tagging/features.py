'''
Created on Nov 14, 2014

@author: rgeorgi
'''

class Feature(object):
	def __init__(self, token):
		self.token = token
		
	def prefix(self, n=3):
		return self.form[:n]
	
	def suffix(self, n=3):
		return self.form[-n:]
	
	@property
	def form(self):
		return self.token.seq
	
	@property
	def label(self):
		return self.token.label

class SequenceFeature(Feature):
	
	def __init__(self, seq, i=0):
		self.i = i
		self.seq = seq
		
	
	def _token(self):
		if self.i < 0 or self.i >= len(self.seq):
			return None
		else:
			return self.seq[self.i]
		
	@property
	def form(self):
		t = self._token()
		if not t:
			return '**NONE**'
		else:
			return t.seq.lower()
		
	@property
	def label(self):
		return self._token().label
		
		
	def advance(self):
		self.i += 1
		
	def prev(self):
		return SequenceFeature(self.seq, i = self.i-1)
	
	def next(self):
		return SequenceFeature(self.seq, i = self.i+1)
	
	def __bool__(self):
		return self.i >= 0 and self.i < len(self.seq)
		
		