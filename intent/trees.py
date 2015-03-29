
from nltk.tree import ParentedTree, Tree
import re
from collections import defaultdict
import sys
import unittest
import intent.alignment.Alignment
from copy import copy
import itertools



class IdTree(ParentedTree):
	'''
	This is a tree that inherits from NLTK's tree implementation,
	but assigns IDs that can be used in writing out the Xigt format.
	'''
	def __init__(self, node, children=None, id=None, index=None):
		super().__init__(node, children)
		self.id = id
		self.index = index
	
	def __eq__(self, other):
		q = ParentedTree.__eq__(self, other)
		return q and (self.id == other.id) and (self.index == other.index)
			
	
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
	
	def find(self, index = None, id = None):
		
		# Must search by either id or index
		assert id or index
		
		index_q = (index is None) or (self.index == index)
		id_q    = (id is None) or (self.id == id)
		
		if index_q and id_q:
			return self
		
		elif self.is_preterminal():
			return None
		else:
			ret = None
			for child in self:
				found = child.find(index, id)
				if found is not None:
					ret = found
					break
			return ret
				
	
	def delete(self):
		'''
		Delete self from parent.
		'''
		del self.parent()[self.get_idx]
		
	
	def copy(self):
		'''
		Perform a deep copy
		'''
		if self.is_preterminal():
			return IdTree(self.label(), copy(self), id=self.id, index=self.index)
		else:
			new_children = [t.copy() for t in self]			
			return IdTree(self.label(), new_children, id=self.id, index=self.index)
	
	@classmethod
	def fromstring(cls, s, id_base='', **kwargs):
		t = super(IdTree, cls).fromstring(s, **kwargs)
		t.assign_ids()
		for i, pt in enumerate(t.preterminals()):
			pt.index = i+1
		return t
	
	def preterminals(self):
		return self.subtrees(filter=lambda t: t.height() == 2)
	
	def nonterminals(self):
		return self.subtrees(filter=lambda t: t.height() > 2)
	
	def is_preterminal(self):
		return self.height() == 2
	
	def index_pairs(self):
		for st in self.subtrees():
			for child in st:
				yield((st.index, child.index)) 
				
	def span(self):
		'''
		Return the span of indices covered by this node.
		'''
		
		# 1) If this node is a preterminal, just return
		#    the (1,1) pair of indices for this node.
		
		if self.is_preterminal():
			return (self.index, self.index)
		
		# 2) If we only have one child, then simply
		#    return the span of that child.
		elif len(self) == 1:
			return self[0].span()
		
		# 3) Otherwise, return a span consisting of
		#    the (leftmost, rightmost) indices of the
		#    children.
		else:
			return (self[0].span()[0], self[-1].span()[1])
			
	@property
	def get_idx(self):
		if not self.parent():
			return None
		else:
			return list(self.parent()).index(self)
	
	
	def promote(self):
		'''
		Delete this node and promote its children
		'''
		
		# Get the index of this node, and a ref
		# to its parent, then delete it.
		my_idx = self.get_idx
		parent = self.parent()
		self.delete()
		
		# For each of that node's children,
		# remove their parent attribute
		# then re-add them to the parent
		# where the old node had been.
		for i, child in enumerate(self):	
			child._parent = None
			parent.insert(my_idx+i, child)
			
	def swap(self, i, j):
		'''
		Swap the node indices i and j.
		:param i:
		:type i: int
		:param j: 
		:type j: int
		'''
		i_n = self[i]
		j_n = self[j]
		
		
		# The NLTK Tree throws a fit if we try to "insert"
		# trees without first "zeroing out" the old one.
		self[i] = None
		self[j] = None
		
		self[i] = j_n
		self[j] = i_n
		
	def merge(self, i, j):
		'''
		Merge the node indices i and j
		
		:param i:
		:type i: int
		:param j:
		:type j: int
		'''
		
		assert i != j, 'indices cannot be equal in a merge'
		assert i < j, 'i must be smaller index'
		
		i_n = self[i]
		j_n = self[j]
		
		del self[i]
		del self[j-1]
		
		# Create the new node that is a "+" combination of
		# the labels, and just the child of the first.
		newlabel = '{}+{}'.format(i_n.label(), j_n.label())
		for child in i_n:
			if isinstance(child, Tree):
				child._parent = None
				
		n = IdTree(newlabel, list(i_n), index=i_n.index, id=i_n.id)
		
		
		self.insert(i, n)
		
		
		
		
		
		
		
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
	
def project_ps(src_t, tgt_w, aln):
	'''
	1) Copy the English PS, and remove all unaligned English words.
	2) Replace each English word with the corresponding target words.
	   * If an English word x aligns to several target words,
	     make copies of the node, one copy for each such word.
	     The copies will all be siblings.
	
	3) Start from the root of the projected	PS and for each node
	    x with more than one child, reorder each pair of x’s children until
		they are in the correct order.
			* Let y_i and y_j be two children of x
			* Spans are:
				* S_i = [a_i,b_i]
				* S_j = [a_j,b_j]
			* Reordering y_i and y_j gives four scenarios:
				* S_i and S_j don't overlap.
					* Put y_i before y_j if a_i < a_j
					* Put y_i after  y_j if a_i > a_j
					
				* S_i is contained within S_j
					* Remove y_i and promote its children
				
				* S_j is contained with S_i
					* Remove y_j and promote its children
					
				* S_i and S_j overlap, but neither contains
				  the other.
				  	* Remove both, promote their children
				  	* If they are both leaf nodes with the
				  	* Same span, merge them. (IN+DT, for example)
				  	 
	4) Reattach unaligned words.
		* For each unaligned word x:
			* Find closest left and right aligned neighbor
			* Attach x to the lowest common ancestor of the two.
	'''
	
	src_is = [x[0] for x in aln]
	
	# 1) Copy the English PS... ---	
	tgt_t = src_t.copy()
	
	# 1b) Remove unaligned words... ---
	for pt in tgt_t.preterminals():
		if pt.index not in src_is:

			# Get the child's index in the parent's list,
			# and delete it that way.	
			child_idx = list(pt.parent()).index(pt)
			del pt.parent()[child_idx]
		
	# 2) Replace all the English words with the foreign words ---
	#    (and their indices!)
	aln = sorted(aln, key=lambda x: x[1])
	
	# If we swap the nodes immediately, then we won't be able to
	# search by index correctly, so let's compile a list and then
	# do the swap.
	nodes_to_swap = []
	
	
	for src_i, tgt_i in aln:
		
		# Get the node for the new tree...
		tgt_n = tgt_t.find(index = src_i)
		
		# This must be a preterminal...
		assert(tgt_n.is_preterminal())
		
		# Get the correct word for the index...
		w = tgt_w.get_index(tgt_i)
		
		nodes_to_swap.append((tgt_n, w))
		
	# Now, let's do the swapping.
	for node, word in nodes_to_swap:
		node[0] = word.get_content()
		node.index = word.index
		
		
	# 3) Reorder all nodes with 2 or more children... ---
	nodes_to_examine = list(tgt_t.subtrees(filter=lambda x: len(x) >= 2))
	for node in nodes_to_examine:
		
		# Try each combination pairwise... 
		for s_i, s_j in itertools.combinations(node, 2):
			a_i, b_i = s_i.span()
			a_j, b_j = s_j.span()
			
			# TODO: Check that this logic is sound
			# We may have manipulated the node 
			# such that the next permutation is invalid.
			# In that case, let's skip it.
			if s_i not in node:
				continue
			if s_j not in node:
				continue
			
			s_i_idx = list(node).index(s_i)
			s_j_idx = list(node).index(s_j)
						
			# 3a) The nodes are already in order. Do nothing. ---
			if a_i < a_j and b_i < b_j:
				pass
				
			# 3b) The nodes are swapped. ---
			elif a_i > a_j and b_i > b_j:
				node.swap(s_i_idx, s_j_idx)
				# TODO: Write a testcase for swap
				
				
			# 3c-i) S_i contains S_j              ---
			# delete s_i and promote its children.		
			elif a_i < a_j and b_i > b_j:
				nodes_to_examine.append(s_i.parent())
				s_i.promote()
				
			
			# 3c-ii) S_j contains S_i ---
			#  delete s_j and promote its children.
			elif a_i > a_j and b_i < b_j:
				nodes_to_examine.append(s_j.parent())
				s_j.promote()
				
			# d) S_j and S_i overlap but are not subsets. ---      
			
			
			# 3di) They are the same span. ---
			#    Merge them
			elif a_i == a_j and b_i == b_j:
				node.merge(s_i_idx, s_j_idx)
				
				# TODO: Write a test case for merge
								
			# 3dii) They are different ---
			# Promote both of them.
			else:
				if not s_i.is_preterminal():
					s_i.promote()
				if not s_j.is_preterminal():
					s_j.promote()
					
				nodes_to_examine.append(node)
				
	# 4) Time to reattach unattached tgt words. ---
	
	unaligned_tgt_words = [w for w in tgt_w if w.index not in [t for s, t in aln]]
	
	
	for unaligned_tgt_word in unaligned_tgt_words:
		left_words = [w for w in tgt_w if w.index < unaligned_tgt_word.index]
		right_words= [w for w in tgt_w if w.index > unaligned_tgt_word.index]
		
		assert left_words or right_words, "Unless none of the words are aligned..."

		left_word = None if not left_words else left_words[-1]
		right_word= None if not right_words else right_words[0]

		t = IdTree('UNK', [unaligned_tgt_word.get_content()], id=unaligned_tgt_word.id, index=unaligned_tgt_word.index)
		

		# If there's only the right word, attach to that.		
		if not left_word:
			left_n = tgt_t.find(index=right_word.index)
			left_idx = left_n.get_idx
			
			left_n.parent().insert(left_idx, t)
			
		# If there's only the left word, attach to that.
		elif not right_word:
			right_n = tgt_t.find(index=left_word.index)
			right_idx = right_n.get_idx
			right_n.parent().insert(right_idx+1, t)
			
		# TODO: What if there is both a left and a right.
		else:
			left_n = tgt_t.find(index=left_word.index)
			right_n= tgt_t.find(index=right_word.index)
	
	return tgt_t

	
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

class SpanTest(unittest.TestCase):
	
	def setUp(self):
		self.t = IdTree.fromstring('''(ROOT
  (SBARQ
    (WHNP (WP Who))
    (SQ (VBP do) (NP (PRP you)) (VP (VB believe) (VP (VBN called))))))'''
    )
		
	def test_span(self):
		self.assertEqual(self.t.span(), (1,5))
	
class ProjectTest(unittest.TestCase):
	
	def setUp(self):
		self.t = IdTree.fromstring('''
(S
	(NP
		(DT The)
		(NN teacher)
	)
	(VP
		(VBD gave)
		(NP
			(DT a)
			(NN book)
		)
		(PP
			(IN to)
			(NP
				(DT the)
				(NN boy)
			)
		)
		(NP
			(NN yesterday)
		)
	)
)''')
		self.proj = IdTree.fromstring(
'''(S
	(VBD rhoddodd)
	(NP
		(DT yr)
		(NN athro)
	)
	(NP
		(NN lyfr)
	)
	(PP
		(IN+DT i'r)
		(NN bachgen)
	)
	(NP
		(NN ddoe)
	)
)''')
		self.aln = intent.alignment.Alignment.Alignment([(1,2), (2,3), (3,1), (5,4), (6, 5), (7, 5), (8, 6), (9, 7)])
		
	def test_proj(self):
		proj = project_ps(self.t, RGWordTier.from_string("rhoddodd yr athro lyfr i'r bachgen ddoe"), self.aln)

		# Reassign the ids after everything has moved around.		
		proj.assign_ids()
		
		self.assertEqual(self.proj, proj)
		
class PromoteTest(unittest.TestCase):
	
	def setUp(self):
		self.t = IdTree.fromstring('(S (NP (DT the) (NN boy)) (VP (VBD ran) (IN away)))')
	
	def test_equality(self):
		t2 = self.t.copy()
		t3 = self.t.copy()
		self.assertEqual(self.t, t2)
		
		t2.find(1).delete()
		self.assertNotEqual(self.t, t2)
		
		# Change the id
		t3n = t3.find(1)
		t3id = t3n.id
		t3idx = t3n.index
		
		t3n.id = 'asdf'
		
		self.assertNotEqual(self.t, t3)
		
		# Change it back.
		t3n.id = t3id
		self.assertEqual(self.t, t3)
		
		# Change the index
		t3n.index = -1
		self.assertNotEqual(self.t, t3)
		
		# Change it back
		t3n.index = t3idx
		self.assertEqual(self.t, t3)
		
	def test_promote(self):
		t2 = self.t.copy()
		t3 = self.t.copy()
		vp = self.t[1]
		vp.promote()
		
		self.assertNotEqual(self.t, t2)
		self.assertEqual(t2, t3)
		
		
from intent.igt.rgxigt import RGWordTier