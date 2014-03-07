'''
Created on Sep 6, 2013

@author: rgeorgi
'''
import re
from nltk.corpus.reader.util import read_sexpr_block
import nltk.tree
import sys
import chardet


def break_bracket(bracket_string):
	'''
	break_bracket:
	
	Given a PTB-style bracket: (NP (NN DOG)), extract the label
	for the node and the next set of matched brackets that make up
	its children.
	'''
	brackets = 0  # (How many open parens there are)
	label, children = '',[]
	buffer = '' # This will be our currently-being-formed subbracket.
	
	# For each character in the string...
	for i in range(len(bracket_string.strip())):
		c = bracket_string[i]
		buffer += c
		
		# Add/subtract brackets...
		if c == '(':
			brackets += 1
		elif c == ')':
			brackets -= 1
			
			# Each time we count down to 1 bracket, whatever's
			# Accumulated inside the buffer is a child.
			if brackets == 1:
				children.append(buffer)
				buffer = ''
				
			# Once we've reached zero, we've parsed the whole current
			# part of the string.
			if brackets == 0 and buffer[:-1].strip():
				children.append(buffer[:-1])
				
		elif re.match('\s',c) and not label:
			label = buffer[1:].strip()
			if not label.strip():
				label = 'ROOT'
			buffer = ''
				
			
						
		if brackets == 0:
			break

	return label, children

def parse_ptb_file(path, simplify = False, traces = False):
	
	ptb_file = open(path, 'r')

	block = read_sexpr_block(ptb_file)
	ptb_trees = []
	while block:
		for s in block:
			t = nltk.tree.Tree.parse(s)
			ptb_trees.append(t)
		block = read_sexpr_block(ptb_file)

	ptb_file.close()
	
	return ptb_trees


#===============================================================================
#  Tree Class
#===============================================================================

class Tree():
	def __init__(self, label, id = None):
		self.children = []
		self.id = id
		self.parent = None
		self.label = label
	
	
	def depth(self, count=0):
		if not self.parent:
			return count
		else:
			return self.parent.depth(count+1)
	
	def index(self, item):
		return self.children.index(item)
	
	
	def insert(self, index, child, typecheck = True):
		if typecheck and child.__class__ != self.__class__:
			raise Exception('Tried to insert an object that is not a tree to the tree!')
		child.parent = self
		self.children.insert(index, child)
		return child
	
	def append(self, child, typecheck = True):
		
		if typecheck and (not isinstance(child, self.__class__)):
			raise Exception('Tried to append an object that is not a tree to the tree!')
		child.parent = self   
		self.children.append(child)
		return child
	
	def __nonzero__(self):
		'''
		Any tree that has a label is not null. If it has zero children, it's just a leaf node.
		'''
		return True
	
	def __len__(self):
		return len(self.children)
		
	def ancestors(self):
		if not self.parent:
			return []
		else:
			return [self.parent] + self.parent.ancestors()
		
	def nodes(self, include_root = False, ordered = True):
		nodes = self.nodes_h(include_root)
		if ordered:
			nodes.sort(key = lambda node: node.order)
		return nodes
		
	def nodes_h(self, include_root = False):		
		nodes = []
		if self.parent or include_root:
			nodes.append(self)
		for child in self.children:
			nodes += child.nodes_h()
			
		return nodes
		
	def leaves(self, ls = [], ordered = False):
		if not self.children:
			return [self]
		else:
			ls = []
			for child in self.children:
				ls += child.leaves(ls)
				
			if ordered:
				ls.sort(key=lambda leaf: int(leaf.order))
			return ls
		
	def flatten(self, ordered = True):
		ret_str = ''
		
		leaves = self.leaves()
		
		if ordered:
			leaves.sort(key=lambda leaf: int(leaf.order))
		
		
		for leaf in self.leaves():
			ret_str += str(leaf.label)+' '
		return ret_str.strip()
		
	def find_root(self):
		if not self.parent:
			return self
		else:
			return self.parent.find_root()
		
	
	def __getitem__(self, i):
		return self.children[i]
	
	def remove_labels(self, labellist, promote_children):
		labels = self.find_labels(labellist)
		while labels:
			for l in labels:
				try:
					l.remove_node(promote_children, True)
				except:
					labels.remove(l)
	
	def find_labels(self, labellist):
		
		ret_children = []
		
		label_matches = filter(lambda label: re.search(label, self.label), labellist)
		pos_matches = []
		if isinstance(self, Terminal):
			pos_matches = filter(lambda label: re.search(label, self.pos), labellist)
		
		if label_matches or pos_matches:
			ret_children += [self]
		
#		if self.label in labellist or (isinstance(self, Terminal) and self.pos in labellist):
#			return [self]
		
		for child in self.children:
			ret_children += child.find_labels(labellist)
			
		return ret_children

		
		
		
	def remove_node(self, promote_children = True, prune_empty = False):
		parent = self.parent
		
		# Get the index where the old node was...
		index = parent.children.index(self)
		
		# Remove the child from the parent's children...
		parent.children.remove(self)
		
		# If the parent previously had children and now does not, prune it.
		if prune_empty and len(parent.children) == 0:
			
			parent.remove_node(promote_children, prune_empty)
		
		if promote_children:
			pos = index
			# Also make sure any children of the removed node have their parents
			# made the old node's parents...
			for child in self.children:
				parent.insert(pos, child)
				pos += 1
		else:
			self.children = []

#===============================================================================
#  Phrase Tree Class
#===============================================================================


class PhraseTree(Tree):
	def __init__(self, label, id=None):
		Tree.__init__(self, label, id=id)
		
	def __repr__(self):
		return '<PhraseTree "%s">' % self.label
		
	def __str__(self):
		if not self.children:
			return str(self.label)
		else:
			ret_str = '(%s' % self.label
			for child in self.children:
				ret_str += ' %s' % child
			return ret_str + ')'
		
class Nonterminal(PhraseTree):
	def __init__(self, label, id=None, deptype=None):
		self.deptype=deptype
		PhraseTree.__init__(self, label, id=id)
		
	def get_by_order(self, order):
		child_found = None
		for child in self.children:
			child_found = child.get_by_order(order)
			if child_found:
				break
		return child_found
		
	def __str__(self):
		ret_str = '(%s [%s %s]' % (self.label, self.id, self.deptype)
		for child in self.children:
			ret_str += ' %s' % child
		return ret_str + ')'

class Terminal(PhraseTree):
	def __init__(self, label, pos, id=None, order=0, deptype = None):
		self.pos = pos
		self.deptype = deptype
		self.order = order
		PhraseTree.__init__(self, label, id=id)
		
	def get_by_order(self, order):
		if self.order == order:
			return self
		else:
			return False
		
	def __str__(self):
		return '(%s [%s %s] %s)' % (self.pos, self.id, self.deptype, self.label)

			
#===============================================================================
#  Parsing Routines
#===============================================================================

def parse_ptb_string(ptb_string, root = True, simplify=True, traces = False):

	pos, children = break_bracket(ptb_string.strip())
	if simplify:
		pos = pos.split('-')[0]
	t = Nonterminal(pos)
		
	if not children[0].startswith('('):
		assert len(children) == 1 # (Make sure a missing bracket means this is a terminal node)
		word = children[0]
		
		# Skip traces...
		if not traces and (word.startswith('*') or pos == '-NONE-'):			
			t = Terminal('','')
		else:
			t = Terminal(word, pos)
	else:
		for child in children:
			# Only treat the first go-through as the root...
			childtree = parse_ptb_string(child, False, simplify, traces)
			if childtree:
				t.append(childtree, typecheck = False)
			
	# If we have the root, assign "order" attributes based on depth-first
	# order of its leaf nodes.
	if root:
		leaves = t.leaves()
		order = 1
		for leaf in leaves:
			leaf.order = order
			order += 1
	return t
			
