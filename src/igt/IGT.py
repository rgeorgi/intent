'''
Created on Aug 26, 2013

@author: rgeorgi
'''

class IGT(object):
	'''
	Representation for an IGT instance.
	'''


	def __init__(self):
		self.id = None
		self.lang_id = None
		self.lang = None
		self.gloss = None
		self.trans = None
		'''
		Constructor
		'''
		
		
	def __repr__(self):
		return '<IGT id="%s">' % (self.id)
		
