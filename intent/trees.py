
from nltk.tree import Tree, ParentedTree
from unittest.case import TestCase
from intent.igt.rgxigt import RGTier, rgp, RGItem, RGWordTier

class XigtTree(ParentedTree):
	'''
	This is a tree that inherits from NLTK's tree implementation,
	but assigns IDs that can be used in writing out the Xigt format.
	'''
	def __init__(self, node, children=None, id=None):
		super().__init__(node, children)
		self.id = id
				
	@classmethod
	def fromstring(cls, s, id_base='', **kwargs):
		t = super(XigtTree, cls).fromstring(s, **kwargs)
		
		
		for i, st in enumerate(t.subtrees()):
			st.id = '%s%d' % (id_base, i+1)
		return t
		

		