'''
Created on Oct 23, 2013

@author: rgeorgi
'''
class Edge(object):
	'''
	An Edge object is just an ordered pair of <child, parent> identifiers.
	'''
	def __init__(self, child, parent):
		self.child = child
		self.parent = parent
	def __eq__(self, o):
		return (isinstance(o, Edge) and
				self.parent == o.parent and
				self.child == o.child)
	def __str__(self):
		return '<%s, %s>' % (self.child, self.parent)
	def __repr__(self):
		return '<EDGE: %s, %s>' % (self.child, self.parent)
	def __hash__(self):
		return (self.child, self.parent).__hash__()
