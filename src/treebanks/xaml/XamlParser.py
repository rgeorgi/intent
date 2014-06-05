'''
Created on Apr 30, 2014

@author: rgeorgi
'''

from xml.dom import minidom
from utils.xmlutils import get_child_tags, find_tag, getIntAttr, get_ref
import sys
from utils.Token import Tokenization, Token, morpheme_tokenizer, tokenize_string
from corpora.IGTCorpus import IGTTier, IGTToken, Span
from tokenize import tokenize
import re
import xml.sax
from xml.sax.saxutils import XMLFilterBase, XMLGenerator
import os

class XAMLElement(object):
	def __init__(self, name, text, type=None):
		self.name = name
		self.text = text
		self.type = type
		
	def __getitem__(self, idx):
		return self.text.__getitem__(idx)


class XAMLData(object):
	def __init__(self):
		self.docid = None
		self.lines = None
		self.name = None
		
		self.lang = None
		self.gloss = None
		self.trans = None
		
		self.gloss_pos = None
		
		
	def __setitem__(self, k, v):
		self._dict[k] = v
	def __getitem__(self, k):
		return self._dict[k]
	
	def has_segs(self):
		return self.lang and self.gloss and self.trans
	
	def has_pos(self):
		return self.gloss_pos
	
	def __hash__(self):
		return str(self.name)
		
class XamlParser(object):
	def __init__(self):
		pass
	
	def parse(self, fp):
		parser = xml.sax.make_parser()
		
		# Original filename
		prefix = os.path.splitext(fp)[0]
		
		downstream_handler = XMLGenerator(open(prefix+'-filtered.xml', 'w'))
		filter_handler = LGTFilter(parser, downstream_handler)
		filter_handler.parse(fp)


		
class LGTFilter(XMLFilterBase):
	
	def __init__(self, upstream, downstream):
		XMLFilterBase.__init__(self, upstream)
		self._downstream = downstream
		
		# Queue Variables 
		self.queue = []
		self.tiers = set([])
		
		self.last_docid = None
		self.cur_docid = None
		self.cur_docid_count = 0
		
		self.skip = False
		
		self.in_igt = False
	
	
	def startElement(self, name, attrs):
		if name == 'TextTier':
			tt = attrs['TierType']
			
			#===================================================================
			# Skip this instance if there is corruption in the tier type.
			#===================================================================
			if 'CR' in tt:
				self.skip = True
				
			#===================================================================
			# Add the tier type to the set of types.
			#===================================================================
			if tt != 'odin-txt':
				self.tiers.add(tt[0])
			
		self.queue.append(lambda: self._downstream.startElement(name, attrs))
		
		#=======================================================================
		# Set the "in_igt" flag if we are inside an igt instance.
		#=======================================================================
		if name == 'Igt':
			self.in_igt = True
			
			# Keep track of the current and previous docid
			self.last_docid = self.cur_docid
			self.cur_docid = attrs['DocId']
			
			if self.last_docid != self.cur_docid:
				self.cur_docid_count = 0	
		
		
	def characters(self, content):
		self.queue.append(lambda: self._downstream.characters(content))
		
	def endElement(self, name):		
		
		#=======================================================================
		# If we are closing an IGT element, check to see if we want to pass it on,
		# or if we want to block it because of corruption or other reasons.
		#=======================================================================
		if name == 'Igt':
			
			#===================================================================
			# Check to see if we have the requisite tiers to pass the instance
			#===================================================================
			if not {'L','G','T'}.issubset(self.tiers):
				self.skip = True
			
			#===================================================================
			# Increment the number of instances for this docid
			#===================================================================
			if not self.skip and self.last_docid == self.cur_docid:
				self.cur_docid_count += 1
			
			#===================================================================
			# Limit the number of allowed instances per docid to 3
			#===================================================================
			if self.cur_docid_count >= 3:
				self.skip = True
			
			#===================================================================
			# Only process the queue if the skip flag is not set. 
			#===================================================================
			if not self.skip:
				for f in self.queue:
					f()
				self._downstream.endElement(name)

			#===================================================================
			# Now, reset the filter.
			#===================================================================
			self.queue = []
			self.tiers = set([])
			self.skip = False
			self.in_igt = False
			
		#=======================================================================
		# If we are not closing an IGT element, but we are still inside an IGT,
		# queue the event.
		#=======================================================================
		elif self.in_igt:
			self.queue.append(lambda: self._downstream.endElement(name))
			
		#=======================================================================
		# Process as normal if we are not inside an IGT element.
		#=======================================================================
		elif not self.in_igt:
			self._downstream.endElement(name)
			
		
			
	
		
	