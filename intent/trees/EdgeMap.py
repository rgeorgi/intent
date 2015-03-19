'''
Created on Oct 23, 2013

@author: rgeorgi
'''
import utils.SetDict
import trees.DepTree
from trees.Edge import Edge


class EdgeMap():
	def __init__(self, edges = []):
		self.child_dict = utils.SetDict()
		self.parent_dict = utils.SetDict()
		for e in edges:
			self.child_dict.add(e.parent, e.child)
			self.parent_dict.add(e.child, e.parent)
	
	def contains_child(self, child):
		return child in self.parent_dict
	
	def add(self, edge):
		self.child_dict.add(edge.parent, edge.child)
		self.parent_dict.add(edge.child, edge.parent)
	
	def get_roots(self):
		return self.child_dict[-1]
	
	def copy(self):
		em = EdgeMap(self.get_edges())
		return em		
	
	def get_tree(self, terms, root_id = None, root_label = None):
		root_node = DepTree.DepTree(root_label, root_id, root=True, order=-1)
		root_children = self.get_children(-1)

		for root_child in root_children:
			child_node = self._get_tree_h(root_child, terms, [])
			if child_node:
				root_node.append(child_node)
		return root_node
		
	def remove_edge(self, e):
		child = e.child
		parent = e.parent
		self.parent_dict.remove_value(child, parent)
		self.child_dict.remove_value(parent, child)
		
	def _get_tree_h(self, index, terms, visited_indices = []):
		
		term = terms.find_order(index)
		if not term:
			return None
		t = DepTree.DepTree(term.label, term.id, term.pos, order=index)
		
		for child in self.get_children(index):
			# skip children that have appeared already (as
			# an ancestor, presumably)
			if child in visited_indices:
				continue
			
			child_t = self._get_tree_h(child, terms, visited_indices+[child])
			if child_t:
				t.append(child_t)
		return t
	
	def depth(self, index):
		return self._depth(index, set([]))
	
	def _depth(self, index, seen_indices = set([])):
		'''
		Use this helper function so that we can avoid cycles...
		'''
		if not self.get_parents(index):
			return 0
		else:
			depths = []
			parents = self.get_parents(index)
			
			for parent in self.get_parents(index):
				if parent not in seen_indices:
					depths.append(self._depth(parent, seen_indices|set([index])))
			if not depths:
				return 1
			else:
				return min(depths) + 1
	

		
	
	def remove_index(self, index, removal_list = []):
		''' Remove the given index, and make the parent
			of the removed node the parent of the removed
			node's children.'''
		
		if index not in self.parent_dict:
			new_parents = []
		else:
			new_parents = self.parent_dict[index]
			
		if index in self.parent_dict:
			# Remove all the entries for that parent from
			# the mapping.
			del self.parent_dict[index]

		

		old_children = []
		if index in self.child_dict:
			old_children = self.child_dict[index].copy()
			for child in old_children:
				
				# Recurse down to make sure we get all the
				# children...
				if child in removal_list:
					self.remove_index(child, removal_list)
				
				self.child_dict.remove_value(index, child)
				self.child_dict.remove_key(index)
				self.parent_dict.remove_value(child, index)
				for new_parent in new_parents:
					self.parent_dict.add(child, new_parent)
					self.child_dict.add(new_parent, child)
					
		
			
		# Make sure to check for leaves, too:
		for parent in self.child_dict.keys():
			cur_children = self.child_dict[parent].copy()
			for child in cur_children:
				if child == index:
					self.child_dict.remove_value(parent, child)
	
	
	def get_indices(self):
		return (set(self.child_dict.keys()) | set(self.parent_dict.keys())) - set([0])
	
	def get_edges(self):
		edges = []
		for parent in self.child_dict.keys():
			for child in self.child_dict[parent]:
				e = Edge(child, parent)
				edges.append(e)
		return edges 
	
	def get_parents(self, index):
		if index in self.parent_dict:
			return self.parent_dict[index]
		else:
			return []
		
	def get_children(self, index):
		if index in self.child_dict:
			return self.child_dict[index]
		else:
			return []
		
	def get_ancestors(self, index):
		return self._get_ancestors_h(index, [])
		
	def _get_ancestors_h(self, index, tail):
		parents = self.get_parents(index)
		
		for parent in parents:
			if parent not in tail:
				tail.append(parent)
				self._get_ancestors_h(parent, tail)
		return tail
			
