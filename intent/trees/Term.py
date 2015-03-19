'''
Created on Oct 23, 2013

@author: rgeorgi
'''

class Term():
	def __init__(self, label, id = None, order = -1, pos = None):
		self.label = label
		self.id = id
		self.order = order
		self.pos = pos
		
	def __str__(self):
		return '<"%s" [%s]>' % (self.label, self.id)
	
	def __repr__(self):
		return str(self)
	
	def __eq__(self, other):
		return self.id == other.id
	
	
class TermList(list):
	def __init__(self):
		super(list)
		
	def find_id(self, id):
		found = None		
		for t in self:
			if t.id == id:
				found = t
				break
		return found
	
	def index_id(self, id):
		found = self.find_id(id)
		if found:
			return self.index(found)
		else:
			return -1
		
	def find_order(self, order):
		found = None
		for t in self:
			if t.order == order:
				found = t
				break
		return found
	
	def index_order(self, order):
		found = self.find_order(order)
		if found:
			return self.index(found)
		else:
			return None
		
		
		