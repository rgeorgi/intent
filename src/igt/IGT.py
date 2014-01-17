'''
Created on Aug 26, 2013

@author: rgeorgi
'''
import re
import sys

class IGT(object):
	'''
	Representation for an IGT instance.
	'''

	def _parse(self, text):
		lang_match = re.search('tag=L.*?:(.*)$', text, flags=re.M)
		gloss_match = re.search('tag=G.*?:(.*)$', text, flags=re.M)
		trans_match = re.search('tag=T.*?:(.*)$', text, flags=re.M)		
		identifier = re.search('doc_id=(\S+)\s+(\S+)', text, flags=re.M)
		language_match = re.search('language: (.*)$', text, flags=re.M)
		
		if lang_match:
			self.lang = lang_match.group(1).strip()
		if gloss_match:
			self.gloss = gloss_match.group(1).strip()
		if trans_match:
			self.trans = trans_match.group(1).strip()
		if identifier:
			self.id = '%s.%s' % identifier.groups()
			
			
		if language_match:
			self.lang = language_match.group(1)
	

	def __init__(self, text = None):
		self.id = None
		self.lang_id = None
		self.lang = None
		self.gloss = None
		self.trans = None
		
		self.raw = text
		if text.strip():
			self._parse(text)
	
				
	def __repr__(self):
		ret_str = '<IGT id="%s" lines=%%s>' % (self.id)
		lines = 'L' if self.lang else ''
		lines += 'G' if self.gloss else ''
		lines += 'T' if self.trans else ''
		return ret_str % lines
		
		
		
		
