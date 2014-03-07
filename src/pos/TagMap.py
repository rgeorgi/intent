'''
Created on Aug 30, 2013

@author: rgeorgi
'''
import os
from utils.ListDict import ListDict
import codecs
import chardet
import sys
from utils.encodingutils import utfread, getencoding

class TagMap():
	'''
	This is a simple class for reading/writing the prototype files used by Haghighi's prototype system.
	'''


	def __init__(self, path = None):
		'''
		Constructor
		'''
		self.old_to_new = {}
		self.new_to_old = ListDict()
		
		if path:
			if not os.path.exists(path):
				raise Exception('Tag map "%s" does not exist.' % path)
				
			encoding = getencoding(path)
			f = codecs.open(path, encoding=encoding)
			data = f.read()
			f.close()
			
			lines = data.split('\n')
			
			for line in lines:
				tags = line.split()
				cat = tags[0]
				for datum in tags[1:]:
					self.old_to_new[datum] = cat
					self.new_to_old.add(cat, datum)
					
	def remove_fine(self, fine):
		old_tag = self.new_to_old[fine]
		del self.new_to_old[fine]
		self.old_to_new.remove_value(old_tag, fine)
		del self.old_to_new[old_tag]
					
	def __getitem__(self, key):
		return self.old_to_new[key]
					
	def __str__(self):
		out_str = ''
		for key in self.new_to_old.keys():
			out_str += str(key)
			for elt in self.new_to_old[key]:
				out_str += '\t%s' % elt
			out_str += '\n'
		return out_str
			
	def __nonzero__(self):
		return True
			
			
		