'''
Created on Jan 29, 2011

@author: rgeorgi
'''


import trees, sys
import re
import os
from utils.ListDict import ListDict
from trees.ptb import parse_ptb_file
from utils.xmlutils import get_child_tags, createTextNode
from trees.SmultronDepTree import SmultronDepTree
from trees.DepTree import DepTree
from xml.dom.minidom import Element, parse, getDOMImplementation
import chardet
from utils.encodingutils import getencoding
import codecs


DEBUG = True


	
def node_to_tree(node, root=False):

	cns = get_child_tags(node, 'childnodes')
	
	if node.localName == 'childnodes':
		if node.hasAttribute('xml:id'):
			
			# Get the form... (lemma)
			form = get_child_tags(node, 'form')[0].childNodes[0].data
			
			# Get the pos info...
			pos_tag = get_child_tags(node, 'pos')
			if pos_tag:
				pos_tag = pos_tag[0].childNodes[0].data
				
			# Get the relation type...
			rel_type = get_child_tags(node, 'relation')
			if rel_type:
				rel_type = rel_type[0].childNodes[0].data
				
			# Get the order attribute...
			order = None
			if node.hasAttribute('order'):
				order = node.getAttribute('order')
				
			# Get the gloss...
			gloss = get_child_tags(node, 'gloss')
			if gloss:
				gloss = gloss[0].childNodes[0].data
				
			# Get the ID
			id = node.getAttribute('xml:id')
			t = DepTree(form, id, pos_tag, rel_type, root=root, order=order, gloss=gloss)
			if node.hasAttribute('rootnode'):
				t = trees.SmultronDepTree(form, id, pos_tag, rel_type, root=root, order=order, gloss=gloss, rootnode=node.getAttribute('rootnode'))

		else:
			children = []
			for lm in get_child_tags(node, 'LM'):
				children.append(node_to_tree(lm))


			return children
	elif node.localName == 'LM':
		
		# If there's no "form" element in the LM, it's a root node
		id = node.getAttribute('xml:id')
		label = id
		form = get_child_tags(node, 'form')
		if form:
			label = form[0].childNodes[0].data
			
		# Get the pos tag...
		pos_tag = get_child_tags(node, 'pos')
		if pos_tag:
			pos_tag = pos_tag[0].childNodes[0].data
			
		# Also get the relation type:
		rel_type = get_child_tags(node, 'relation')
		if rel_type:
			rel_type = rel_type[0].childNodes[0].data

		order = 0
		if node.hasAttribute('order'):
			order = node.getAttribute('order')
			
		gloss = get_child_tags(node, 'gloss')
		if gloss:
			gloss = gloss[0].childNodes[0].data
				
		t = trees.DepTree.DepTree(label, id, pos_tag, rel_type, root=root, order=order, gloss=gloss)
		if node.hasAttribute('rootnode'):
			t = trees.SmultronDepTree(form, id, pos_tag, rel_type, root=root, order=order, gloss=gloss, rootnode=node.getAttribute('rootnode'))	

		
		# Now, deal with the children.

	if cns:
		
		children = node_to_tree(cns[0])
		if type(children) == type(t):
			t.append(children, typecheck=False)
		else:
			for child in children:
				t.append(child)
	#print t
	return t

			



def tree_to_LM(tree):
	

	# Always make this an LM. Single children will just be 
	node = Element('LM')
	assert tree.id, str(tree)
	if tree.id:
		node.setAttribute('xml:id', tree.id)

	assert tree.id, 'Tree %s does not have ID' % tree

	
	if tree.order != None:
		node.setAttribute('order', str(tree.order))
	
	# Only add the "form," "pos," and "relation" types...
	if tree.parent:
		form = Element('form')
		form.appendChild(createTextNode(tree.label))
		node.appendChild(form)
		
	# Add the rootnode attribute if it's a smultron tree...
	if tree.__class__ == SmultronDepTree:
		node.setAttribute('rootnode', tree.rootnode)
		
	if tree.pos:
		posNode = Element('pos')
		posNode.appendChild(createTextNode(tree.pos))
		node.appendChild(posNode)
		
	if tree.rel_type:
		relNode = Element('relation')
		relNode.appendChild(createTextNode(tree.rel_type))
		node.appendChild(relNode)

	if tree.gloss:
		glossNode = Element('gloss')
		glossNode.appendChild(createTextNode(tree.gloss))
		node.appendChild(glossNode)
		
#	print tree
#	print tree.children[0]
#	sys.exit()
			
	# If the tree has multiple children, we need a "childnodes" tag...
	if tree.children:
		childnodes = Element('childnodes')
		
		for child in tree.children:
			childXml = tree_to_LM(child)
			
			if len(tree.children) == 1:
				childnodes.setAttribute('order', childXml.getAttribute('order'))
				childnodes.setAttribute('xml:id', childXml.getAttribute('xml:id'))
				childnodes.childNodes = childXml.childNodes
			else:
				childnodes.appendChild(childXml)
				
				
		node.appendChild(childnodes)
			

			
		
	return node	

class NodeAlignment():
	def __init__(self, a, b):
		self.a = a
		self.b = b
	def __str__(self, a_t=None, b_t=None):
			return '<NodeAlignment: (A) %s, (B) %s>' % (self.a, self.b)
	
	def __eq__(self, other):
		return (self.__class__ == other.__class__ and self.a == other.a and self.b == other.b)
	def __ne__(self, other):
		return not self == other
	def copy(self):
		return NodeAlignment(self.a, self.b)
	
	def __repr__(self):
		return str(self)

class ParallelTree():
	def __init__(self, a_tree = None, b_tree = None):
		self.a_tree = a_tree
		self.b_tree = b_tree
		self.edges = []
		self.a_to_b = ListDict()
		self.b_to_a = ListDict()
		
	def align(self, pairs):
		for pair in pairs:
			a_node = self.a_tree.find_id(pair.a)
			b_node = self.b_tree.find_id(pair.b)
			
			if a_node and b_node:			
				self.edges.append((a_node.order, b_node.order))
				self.a_to_b.add(a_node.order, b_node.order)
				self.b_to_a.add(b_node.order, a_node.order)
	
	def _getdict(self, a_to_b):
		if a_to_b:
			return self.a_to_b
		else:
			return self.b_to_a
		

		
	def isUnaligned(self, aChild, a_to_b = True):
		which_dict = self._getdict(a_to_b)			
		return aChild not in which_dict
		
	def isSingle(self, aChild, a_to_b = True):
		which_dict = self._getdict(a_to_b)
		return (aChild in which_dict and len(which_dict[aChild]) == 1)
		
	def isSwap(self, aChild, aParent, a_to_b = True):
		if a_to_b:
			which_dict = self.a_to_b
			srcTree = self.b_tree
		else:
			which_dict = self.b_to_a
			srcTree = self.a_tree
			
		# -- 1) The child or parent is not aligned.
		if (aChild not in which_dict) or (aParent not in which_dict):
			return False
		else:
			bChildren = which_dict[aChild]
			bParents = which_dict[aParent]
						
			swap = False
			for bParent in bParents:				
				bParentNode = srcTree.get_by_order(bParent)
				if bParentNode and bParentNode.parent and bParentNode.parent.order in bChildren:
					swap = True
			return swap
	
	def isLeftMerge(self, aChild, a_to_b = True):
		if a_to_b:
			which_dict = self.a_to_b
			srcTree = self.b_tree
		else:
			which_dict = self.b_to_a
			srcTree = self.a_tree
			
		# -- 1) The child is not aligned:
		if (aChild not in which_dict):
			return False
		else:
			bChildren = which_dict[aChild]
			leftMerge = False
			for childOne in bChildren:
				nodeOne = srcTree.get_by_order(childOne)
				if nodeOne.parent and nodeOne.parent.order in bChildren:					
					leftMerge = True
			return leftMerge
					
					
		
	def isMatch(self, aChild, aParent, a_to_b = True):
		
		if a_to_b:
			which_dict = self.a_to_b
			srcTree = self.b_tree
		else:
			which_dict = self.b_to_a
			srcTree = self.a_tree
								
		
		# -- 1) The child or parent is not aligned.
		if (aChild not in which_dict) or (aParent not in which_dict):
			return False
		else:
			bChildren = which_dict[aChild]
			bParents = which_dict[aParent]
						
			match = False
			for bChild in bChildren:				
				bChildNode = srcTree.get_by_order(bChild)
				if bChildNode.parent and bChildNode.parent.order in bParents:
					match = True
			return match
		
		
		
	

class Alignment():
	def __init__(self):
		self.id = None
		self.a = None
		self.b = None
		
		self.pairs = []
		
	def merge_alignments(self, a_or_b, child_id, parent_id):
		for pair in self.pairs:
			if a_or_b == 'a' and pair.a == child_id:
				pair.a = parent_id
			elif a_or_b == 'b' and pair.b == child_id:
				pair.b = parent_id	
			
		
	def align_trees(self, tree_a, tree_b, reverse=False, trim=True):
		align_a = ListDict()
		align_b = ListDict()
		
		newpairs = []
		
		for pair in self.pairs:
			a_node = tree_a.find_id(pair.a)
			b_node = tree_b.find_id(pair.b)
			
			if a_node and b_node:
				newpairs.append(pair)
				align_a.add(a_node, b_node)
				align_b.add(b_node, a_node)
				
		if reverse:
			return align_b
		else:
			return align_a
		
		# If "trim" is set to true, just replace the old list of pairs
		# with the new one.
		if trim:
			self.pairs = newpairs
			
		
	def read_xml(self, lm):
		self.id = lm.getAttribute('xml:id')
		self.a = get_child_tags(lm, 'tree_a.rf')[0].childNodes[0].data.split('#')[-1]
		self.b = get_child_tags(lm, 'tree_b.rf')[0].childNodes[0].data.split('#')[-1]
		
		if get_child_tags(lm, 'node_alignments'):
			node_alignments = get_child_tags(lm, 'node_alignments')[0]
			lms = get_child_tags(node_alignments, 'LM')
			for lm in lms:			
				a = get_child_tags(lm, 'a.rf')[0].childNodes[0].data.split('#')[-1]
				b = get_child_tags(lm, 'b.rf')[0].childNodes[0].data.split('#')[-1]
				na = NodeAlignment(a, b)
				self.pairs.append(na)
			
		
		
	def toxml(self):
		lm = Element('LM')
		assert self.id		
		lm.setAttribute('xml:id', self.id)
		
		treea = Element('tree_a.rf')
		treea.appendChild(createTextNode('a#%s' % self.a))
		
		treeb = Element('tree_b.rf')
		treeb.appendChild(createTextNode('b#%s' % self.b))
		
		lm.appendChild(treea), lm.appendChild(treeb)
		
		node_alignments = Element('node_alignments')
		lm.appendChild(node_alignments)
		
		for pair in self.pairs:
			pairlm = Element('LM')
			
			arf = Element('a.rf')
			arf.appendChild(createTextNode('a#%s' % pair.a))
			
			brf = Element('b.rf')
			brf.appendChild(createTextNode('b#%s' % pair.b))
			
			pairlm.appendChild(arf), pairlm.appendChild(brf)
			node_alignments.appendChild(pairlm)
			
		return lm
		
			

class Alignments():
	def __init__(self, path = None):
		self.a = None
		self.b = None
		self.sents = []
		self.path = path
		if path:
			self.read_pml(path)

	def get_tups(self):
		a_s = TreeList(self.get_path('a'))
		b_s = TreeList(self.get_path('b'))
		
		a_ids = map(lambda a: a.id, a_s)
		b_ids = map(lambda b: b.id, b_s)
		
		ret_tups = []
		
		for aln in self:
			a_id = aln.a
			b_id = aln.b 
			
			error = False
			
			try:
				a = a_s[a_ids.index(a_id)]
			except:
				sys.stderr.write('ID for a file "%s" not found\n' % a_id)
				error = True
				
			try:
				b = b_s[b_ids.index(b_id)]
			except:
				sys.stderr.write('ID for b file "%s" not found\n' % b_id)
				error = True
			
			if not error:
				ret_tups.append((a,b,aln))
			
		return ret_tups
			
	def get_path(self, which='a'):
		if which == 'a':
			ret_path = self.a
		else:
			ret_path = self.b
		
		if os.path.isabs(ret_path):
			return ret_path
		elif self.path:
			return os.path.abspath(os.path.join(os.path.dirname(self.path), ret_path))

			
	def __getitem__(self, index):
		return self.sents[index]
		
		
	def read_pml(self, path):
		
		encoding = getencoding(path)
		f = codecs.open(path, encoding=encoding)
		
		align_xml = parse(f)
		body = align_xml.getElementsByTagName('body')[0]
		sents = get_child_tags(body, 'LM')
		
		refs = align_xml.getElementsByTagName('reffile')
		for ref in refs:
			if ref.getAttribute('id') == 'a':
				self.a = ref.getAttribute('href')
			else:
				self.b = ref.getAttribute('href')
		
		for sent in sents:
			a = Alignment()
			a.read_xml(sent)
			self.sents.append(a)
		
	
	def __len__(self):
		return len(self.sents)
	
	def __iter__(self):
		return self.sents.__iter__()
		
	def toxml(self):
		root = Element('tree_alignment')
		root.setAttribute('xmlns', 'http://ufal.mff.cuni.cz/pdt/pml/')
		
		# Get all the head stuff taken care of...
		head = Element('head')
		root.appendChild(head)
		
		schema = Element('schema')
		head.appendChild(schema)
		schema.setAttribute('href', 'alignment_schema.xml')
		
		references = Element('references')
		head.appendChild(references)
		
		a_ref = Element('reffile')
		a_ref.setAttribute('id', 'a')
		a_ref.setAttribute('name', 'document_a')
		a_ref.setAttribute('href', self.a)
		
		b_ref = Element('reffile')
		b_ref.setAttribute('id', 'b')
		b_ref.setAttribute('name', 'document_b')
		b_ref.setAttribute('href', self.b)
		
		references.appendChild(a_ref)
		references.appendChild(b_ref)
		
		body = Element('body')
		root.appendChild(body)
		
		for sent in self.sents:
#			print sent.id, sent.a, sent.b
			body.appendChild(sent.toxml())
			
		return root

		
class TreeList(list):
	def __init__(self, path = None):
		self.schema = None
		if path:
			self.read_xml(path)
		super(list)
		
	def read_xml(self, pml_path):
		encoding = getencoding(pml_path)
		
		pml_f = codecs.open(pml_path, encoding=encoding)
		
		pml_doc = parse(pml_f)
		
		schema = pml_doc.getElementsByTagName('schema')[0]
		self.schema = schema.getAttribute('href')
		
		body = pml_doc.getElementsByTagName('body')[0]
		for lm in get_child_tags(body, 'LM'):
			t = node_to_tree(lm)
			t.root = True
			self.append(t)
			
	def read_ptb(self, ptb_path):
		ptb_trees = parse_ptb_file(ptb_path)
		
	def find_id(self, id):
		found = None
		for t in self:
			if t.id == id:
				found = t
				break
		return found
			
		
		
			
	def toxml(self):
		root = Element('conll')
		root.setAttribute('xmlns', 'http://ufal.mff.cuni.cz/pdt/pml/')
		
		head = Element('head')
		root.appendChild(head)
		
		schema = Element('schema')
		head.appendChild(schema)
		schema.setAttribute('href', self.schema)
		
		body = Element('body')
		root.appendChild(body)
		for t in self:
			body.appendChild(tree_to_LM(t))
		return root
		
	
	
		
	


class PML():
	'''
	classdocs
	'''


	def __init__(self, root, schema = None):
		impl = getDOMImplementation()
		self.doc = impl.createDocument(None, root, None)
		
		self.doc.documentElement.setAttribute('xmlns', 'http://ufal.mff.cuni.cz/pdt/pml/')
		
		self.head = self.createElement('head')
		self.doc.documentElement.appendChild(self.head)
		
		self.schema = self.createElement('schema')
		self.head.appendChild(self.schema)
		
		if schema:
			self.setSchema(schema)
		
		self.body = self.createElement('body')
		self.doc.documentElement.appendChild(self.body)
		
	def createElement(self, name):
		return self.doc.createElement(name)
	
	def setSchema(self, schema):
		self.schema.setAttribute('href', schema)
	
		
	def __str__(self):
		return self.doc.toprettyxml()
	

		
		
	
	
	