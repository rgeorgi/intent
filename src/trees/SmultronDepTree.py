'''
Created on Oct 23, 2013

@author: rgeorgi
'''
from trees.DepTree import DepTree

class SmultronDepTree(DepTree):
	def __init__(self, label, id = None, pos = None, rel_type = None, root = False, order = -2, gloss = None, rootnode = None):
		self.rootnode = rootnode
		self.order = order
		DepTree.__init__(self, label, id, pos, rel_type, root, order, gloss)
