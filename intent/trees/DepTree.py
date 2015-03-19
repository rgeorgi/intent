'''
Created on Oct 23, 2013

@author: rgeorgi
'''
from .ptb import Tree
from utils.SetDict import SetDict
import sys
from .Edge import Edge
from .Term import Term, TermList
from .EdgeMap import EdgeMap
import re
from corpora.POSCorpus import POSCorpusInstance, POSToken


class DepTree(Tree):
	'''
	classdocs
	'''
	
	
	
	def __init__(self, label, id = None, pos = None, rel_type = None, root = False, order = -2, gloss = None):
		'''
		Constructor
		'''
		self.root = root
		self.rel_type = rel_type
		self.pos = pos
		self.children = []
		self.order = int(order)
		self.gloss = gloss
		Tree.__init__(self, label, id)
		
	@classmethod
	def edges_to_tree(cls, edges, terms, root_id = None, root_label = 'ROOT'):
		'''
		Given a list of edges and a list of terms, build a dependency
		tree out of it.
		'''
		tree_root = DepTree(root_label, root_id, root=True, order=0)
		
		# Make the lookup dict for children.
		child_dict = SetDict()
		parent_dict = {}
		for edge in edges:
			child_dict.add(edge.parent, edge.child)
			parent_dict[edge.child] = edge.parent
		
		
		# Queue the edges to attach to the tree...
		# (FIFO queue, so that children will be attached to existing nodes
		#  in the tree!)
		process_queue = DepTree._queue_edges(0, child_dict, [])
		
		use_root = True
		# Build the tree!
		while process_queue:
			cur_index = process_queue.pop()
			cur_term = terms[cur_index-1]
			t = DepTree(cur_term.label, id = cur_term.id, pos = cur_term.pos, order = cur_term.order)
			cur_parent = parent_dict[cur_index]
			if cur_parent == 0:
				tree_root.append(t)
			else:
				parent_node = tree_root.get_by_order(cur_parent)
				parent_node.append(t)
		
		return tree_root
	
	def to_pos_corpus_instance(self):
		inst = POSCorpusInstance()
		for node in self.nodes():
			token = POSToken(node.label, node.pos)				
			inst.append(token)
		return inst
	
	def to_snt(self, ordered=True, clean = True):
		ret_str = ''
		nodes = self.nodes()
		if ordered:
			nodes.sort(key=lambda node: node.order)
		for node in nodes:
			label = node.label
			
			if clean:
				label = re.sub('\s+', '', label)
			
			ret_str += '%s ' % label
			
			ret_str = re.sub('[\(\)]', '', ret_str)
			
		return ret_str.strip()
	
	def to_pos(self, delimeter = '/', clean=False):
		ret_str = ''
		nodes = self.nodes()
		nodes.sort(key=lambda node: node.order)
		for node in nodes:
			label = node.label
			if clean:
				label = re.sub('\s+', '', node.label)
				
			ret_str += '%s%s%s ' % (label, delimeter, node.pos)
					
			
		return ret_str.strip()
			
	@classmethod
	def _queue_edges(cls, cur_index, child_dict, queue):
		if cur_index in child_dict:
			for child in child_dict[cur_index]:
				queue.insert(0, child)
				DepTree._queue_edges(child, child_dict, queue)
		return queue
		
	def to_conll(self, hide_heads=False, hide_pos = False, proj_t = None, src_t = None, aln = None, oracle = False, no_predict=False, feat_method = 6, aln_file = sys.stdout):
		'''
		The "hide_heads" parameter removes the head and dependency relation
		columns...
		'''
		
		nodes = self.nodes()
		nodes.sort(key = lambda x: int(x.order))
		
		ret_str = ''
		
	
		src_nodes = []
		proj_nodes = []
		
		if src_t:
			src_nodes = src_t.nodes()
			src_nodes.sort(key = lambda x: int(x.order))
			

			
			
			
		# --- 1) Reassign the order so we don't skip (for maltparser)
		for j in range(len(src_nodes)):
			src_node = src_nodes[j]
			src_node.order = j+1
		
		# --- 1b) Make sure to reassign the order for our own nodes, too
		for i in range(len(nodes)):
			node = nodes[i]
			node.order = i+1
			
		# --- 1c) ...aaand for projected nodes as well.
		if proj_t:
			for k in range(len(proj_nodes)):
				proj_node = proj_nodes[k]
				proj_node.order = k+1
		
			
			
			
		# --- 2) Get the alignments....
		
		
		for na in aln.pairs:
			a_node = src_t.find_id(na.a)
			
			b_node = None
			if proj_t:
				b_node = proj_t.find_id(na.b)
			
			if a_node and b_node:
				a_id = a_node.order
				b_id = b_node.order
			
				ret_str += "*ALIGNMENT	%d	%d\n" % (a_id, b_id)
				
		ret_str += "*FEATMETHOD	%d\n" % feat_method
		
		for src_node in src_nodes:
			ret_str += "*SRCLINE	%d	%s	%s	%d\n" % (src_node.order, src_node.label, src_node.pos, src_node.parent.order)
			
	
				


		# --- 3) Write the predicted heads from the proj_tree...
		
		for i in range(len(nodes)):
			node = nodes[i]
			try:
				predicted_head = str(proj_t.find_id(node.id).parent.order)
			except:
				predicted_head = '0'
			
					
			# ------------------------- END ADDING ALIGNED PREDICTIONS -------------------
			
		
			
			# Get the ID of the head...
			head = 0
			
			if node.parent:
				head = node.parent.order
				if head == -1:
					head = 0
			
			
			
			# Use the hide_heads switch to hide the head
			if hide_heads:
				head = '_'
				
			types = "0,0,0,0"

			# Default to not showing a POS.
			# Only show it if there is one
			# for this node and it's not requested
			# to be hidden.				
			pos = '_'
			if node.pos and not hide_pos:
				pos = node.pos

			# Set the dependency relation
			deprel = '_'
			if node.order == 0:
				deprel = 'ROOT'
				
			
			# The CoNLL format is:
			#
			# 0 - ID
			# 1 - Form
			# 2 - Lemma
			# 3 - Course POS Tag
			# 4 - POS Tag
			# 5 - Morphological Features
			# 6 - Head
			# 7 - Deprel
			# 8 - PHead
			# 9 - PDepRel
			
			# We will add 10... and 11,12
			
			
			feats = [node.label,	# 1 - Form 
					'_',			# 2 - Lemma
					pos,			# 3 - CPOS
					pos,			# 4 - POS
					'_',				# 5 - MorphFeats
					head,			# 6 - Head
					deprel,			# 7 - DepRel
					'_',			# 8 - Phead
					'_',		# 9 - PDepRel
					predicted_head, # 10 - PredictedHeads
					types] # 11 - PredictedHead Types
					
			
			# First, start by adding the parent_index of the current node.
			feat_str = '%s'%node.order
			for feat in feats:
				feat_str += '\t%s'%feat			
			ret_str += feat_str + '\n'
			
			
		if ret_str.strip():
			return ret_str + '\n'
		else:
			return ''
		
		
	def get_edgemap(self):
		return EdgeMap(self.get_edges())
		
	def get_edges(self):
		edges = []
		if self.parent:
			if self.parent.order == 0:
				self.parent.order = -1
			
			e = Edge(self.order, self.parent.order)
			edges.append(e)				
		
		for c in self.children:
			edges += c.get_edges()
			
		return edges
			

	def get_terms(self):
		'''
		Extract the "flat" sentence from the dependency tree. Relies
		on the nodes having their "order" feature specified.
		'''
		tl = TermList()
		nl = self.nodes()
		nl.sort(key = lambda x: int(x.order)) # <-- sort the nodelist.
		for node in nl:
			t = Term(node.label, id = node.id, order = node.order, pos = node.pos)
			tl.append(t)
		return tl



	def get_by_order(self, order):
		if int(self.order) == int(order):
			return self
		else:
			found = None
			for child in self.children:
				found_child = child.get_by_order(order)
				if found_child:
					found = found_child
					break
			return found 

	def copy(self):
		newlabel = self.label
		newid = self.id
		newpos = self.pos
		newreltype = self.rel_type
		
		t = DepTree(newlabel, newid, newpos, newreltype, root = self.root, order = self.order, gloss = self.gloss)
		
		for child in self.children:
			newchild = child.copy()
			t.append(newchild)
		return t
	
	def __hashstr__(self):
		'''
		Helper function for __hash__ that recursively builds a hash out of not only this node, but its children.
		'''
		h_str = str(self.id) + str(self.label)
		for child in self.children:
			h_str += child.__hashstr__()
		return h_str

	def __hash__(self, deep=True):
		return hash(self.__hashstr__())
	
	def __eq__(self, other):
		return hash(self) == hash(other)
	
	def __ne__(self, other):
		return hash(self) != hash(other)
	
	def __nonzero__(self):
		return True
	
	def find_id(self, id, topdown = False):
		# Start from the root if "topdown" is specified.
		# otherwise, this will only look in the subtrees.
		if topdown:
			root = self.find_root()
			return root.find_id(id)
		if self.id == id:
			return self
		else:
			found_node = None
			for child in self.children:
				found_node = child.find_id(id)
				if found_node != None:
					return found_node
			return found_node
		
	def parent_order(self):
		if self.parent:
			return self.parent.order
		else:
			return None
		
	def find_order(self, order, topdown = False):
		# Start from the root if "topdown" is specified.
		# otherwise, this will only look in the subtrees.
		if order == 0:
			return self.find_root()
		if topdown:
			root = self.find_root()
			return root.find_order(order)
		if self.order == order:
			return self
		else:
			found_node = None
			for child in self.children:
				found_node = child.find_order(order)
				if found_node != None:
					return found_node
			return found_node
			
			
	def assign_ids(self, prefix=''):
		i = 0
		for node in self.nodes(include_root = True):
			i += 1
			node.id = '%s%s' % (prefix, i) 


	
	def __strhelp(self, detail=True):
		ret_str = '_%s_(%d)_'%(self.label, self.order)
		if detail:
			ret_str += '[%s' % self.id
			if self.pos:
				ret_str += ' (%s)' % self.pos
			if self.rel_type:
				ret_str += ' *%s*' % self.rel_type
			ret_str += ']'
		return ret_str
	
	def __str__(self, detail=True):
		self.children.sort(key=lambda t: t.order)
		if not self.children:
			return self.__strhelp(detail)
		else:
			#return str(len(self.children))
			ret_str = ''
			for elt in self.children:
				ret_str += str(elt)+' '
			return '(%s %s)' % (self.__strhelp(detail), ret_str.strip()) 
			#return '(_%s_[%s (%s)] %s)' % (self.label, self.id, self.pos, ret_str.strip())
		
	def __repr__(self):
		return '<DepTree "%s">' % self.label
		

		
	def swap_with_parent(self):
		
		oldparent = self.parent
		parentsparent = self.parent.parent
		
		# Get the index that this node was at...
		my_old_index = oldparent.children.index(self)
		
		# Remove me from my parent's children...
		oldparent.children.remove(self)
		
		# Now, get my parent's old position...
		old_parent_index = parentsparent.children.index(oldparent)
		
		# Remove the parent from it's parent
		parentsparent.children.remove(oldparent)
		
		# Re-attach old parent to me.
		self.insert(my_old_index, oldparent)
		
		# Insert this node where the old parent was
		parentsparent.insert(old_parent_index, self, typecheck = False)
	

	
		
	def merge_with_parent(self):
		assert self.parent, 'Node has no parent!'
		
		self.parent.label = self.parent.label + '+' + self.label
		self.parent.remove_id(self.id)
		
		
	def remove_id(self, id, merge_children = True):
		node = self.find_id(id)
		if node:
			parent = node.parent
			
			# Get the index where the old node was...
			index = parent.children.index(node)
			
			# Remove the child from the parent's children...
			parent.children.remove(node)
			
			if merge_children:
				pos = index
				# Also make sure any children of the removed node have their parents
				# made the old node's parents...
				for child in node.children:
					parent.insert(pos, child, typecheck = False)
					pos += 1
				
	def to_ptb(self, ordered=True):
		ret_str = '(%s ' % (re.sub('\s*[\(\)]\s*', '*', self.label))
#		ret_str = '(X '
		
		children = self.children
		if ordered:
			children.sort(key = lambda child: int(child.order))
		for child in children:
			ret_str += child.to_ptb(ordered)
		if not children:
			ret_str += ' X'
		ret_str = ret_str.strip()+') '
		return ret_str
		