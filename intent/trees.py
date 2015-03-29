
from nltk.tree import ParentedTree
import re
from collections import defaultdict

class IdTree(ParentedTree):
	'''
	This is a tree that inherits from NLTK's tree implementation,
	but assigns IDs that can be used in writing out the Xigt format.
	'''
	def __init__(self, node, children=None, id=None, index=None):
		super().__init__(node, children)
		self.id = id
		self.index = index
	
	def assign_ids(self, id_base=''):
		'''
		Assign IDs to the elements of the tree, using the "id_base" string
		as a leading element. 
		|
		Example: `id_base` of `'ds'` would result in `'ds1'`, `'ds2'` etc.  
		
		:param id_base: base which to build the IDs from
		:type id_base: str
		'''
		
		# Per the conventions, we want the preterminals to start from one.
		i = 1
		for st in self.preterminals():
			st.id = '%s%d' % (id_base, i)
			i+=1
		
		for st in self.nonterminals():
			st.id = '%s%d' % (id_base, i)
			i+=1
	
	@classmethod
	def fromstring(cls, s, id_base='', **kwargs):
		t = super(IdTree, cls).fromstring(s, **kwargs)
		t.assign_ids()
		return t
	
	def preterminals(self):
		return self.subtrees(filter=lambda t: t.height() == 2)
	
	def nonterminals(self):
		return self.subtrees(filter=lambda t: t.height() > 2)
	
	def index_pairs(self):
		for st in self.subtrees():
			for child in st:
				yield((st.index, child.index)) 
		
class Word(object):
	def __init__(self, w, i):	
		self.w = w
		self.i = int(i)
		
	def __str__(self):
		return self.w
	def __repr__(self):
		return self.w
	def __hash__(self):
		return hash(self.w)
	def __eq__(self, o):
		return self.w == str(o)
		
def build_tree(dict):
	return DepTree('ROOT', _build_tree(dict, 'ROOT'))
		
def _build_tree(dict, word):
	if word not in dict:
		return []
	else:		
		children = []
		for type, child in dict[word]:
			d = DepTree(child.w, _build_tree(dict, child), type=type, index=child.i)
			children.append(d)
		return children
		
	
	
		
def get_nodes(string):
	nodes = re.findall('(\w+)\((.*?)\)', string)
	
	# We are going to store a dictionary of words
	# and their children, and then construct the
	# tree from "ROOT" on down...
	child_dict = defaultdict(list)
	
	# Go through each of the returned values...
	for name, pair in nodes:
		head, child = pair.split(',')
		
		w_i_re = re.compile('(\S+)-([0-9]+)')
		
		head  = Word(*re.search(w_i_re, head).groups())
		child = Word(*re.search(w_i_re, child).groups())
		
		child_dict[head].append((name, child))
		
	# Now that we have the dictionary, we can start from "ROOT"
	return build_tree(child_dict)
	
class DepTree(IdTree):
	
	def __init__(self, node, children=None, id=None, type=None, index=0):
		super().__init__(node, children, id, index)
		self.type = type
		
	@classmethod
	def fromstring(cls, s, id_base='', **kwargs):
		'''
		Read a dependency tree from the stanford dependency format. Example:
		
		::
		
			nsubj(ran-2, John-1)
			root(ROOT-0, ran-2)
			det(woods-5, the-4)
			prep_into(ran-2, woods-5)
		
		:param s: String to parse
		:type s: str
		:param id_base: ID string on which to base the IDs in this tree.
		:type id_base: str
		'''
		
		t = get_nodes(s)
		t.assign_ids(id_base)
		return t
			
	def __str__(self):
		ret_str = '(%s[%s]' % (self.label(), self.index)
		for child in self:
			ret_str += ' %s' % str(child)
		return ret_str + ')'

		