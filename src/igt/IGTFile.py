'''
Created on Jan 17, 2014

@author: rgeorgi
'''
import re
import sys
from igt.IGT import IGT

class IGTFile(object):
	'''
	classdocs
	'''


	def __init__(self, path):
		'''
		Constructor
		'''
		self.instances = []
		f = file(path, 'r')
		data = f.read()
		f.close()
		
		# Now parse out the individual text instances
		text_instances = re.findall('doc_id[\s\S]+?\n\n', data, flags=re.I)
		self.instances = [IGT(instance) for instance in text_instances ]
		

		
	def glosses(self):		
		return [instance.gloss for instance in self.instances]
	
	
class NAACLFile(IGTFile):
	
	def __init__(self, path):
		self.instances = []
		f = file(path, 'r')
		data = f.read()
		f.close()