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
from xml.sax.saxutils import XMLFilterBase, XMLGenerator, unescape
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
	def __init__(self, **kwargs):
		pass
	
	def parse(self, fp, **kwargs):
		parser = xml.sax.make_parser()
		
		# Original filename
		prefix = os.path.splitext(fp)[0]
		
				
		#=======================================================================
		#  FILTERING AND WRITING
		#=======================================================================
		
		
		# 1) Filter out the instances for annotation.
		filter_handler = LGTFilter(parser)
		
		# 2) Output the gram information for classifiers and taggers.
		output_handler = GramOutputFilter(filter_handler, **kwargs)
		
		# 3) Clean the XML of escape characters.
		output_handler = XMLCleaner(output_handler)
		
		# 4) Write the XML output to file.
		#output_handler = XMLWriter(output_handler, prefix+'-filtered.xml')
		
		output_handler.parse(fp)

def write_gram(gram, pos, **kwargs):
	type = kwargs.get('type')
	output = kwargs.get('output', sys.stdout)
	
	
	if kwargs.get('lowercase'):
		gram = gram.lower()
		
	if kwargs.get('strip', True):
		gram = re.sub('\s*', '', gram)
	
	# Output the grams for a classifier
	if type == 'classifier':
		output.write(pos)
		
		for token in tokenize_string(gram, morpheme_tokenizer):
			output.write('\t%s:1' % token.seq)

		output.write('\n')
		
	if type == 'tagger':
		output.write('%s/%s ' % (gram, pos))

#===============================================================================
# Class for parsing the XAML Text References
#===============================================================================
class XamlRefActionFilter(XMLFilterBase):
	def __init__(self, upstream, **kwargs):
		XMLFilterBase.__init__(self, upstream)
		
		self.textref = {}
		self.typeref = {}
		
		self.kwargs = kwargs
		
	def startElement(self, name, attrs):
		
		# Cache the  text contents.
		if name == 'TextTier' and attrs.get('Text'):
			uid = attrs['Name']
			self.textref[uid] = attrs['Text']
			self.typeref[uid] = attrs['TierType']
			
		# SegPart commands
		if name == 'SegPart':
			uid = attrs['Name']
			backref = attrs['SourceTier'][13:-1]
			type = self.typeref[backref][0]
			text = attrs['Text']
			self.textref[uid] = text
			self.typeref[uid] = type
			
		# POS Tier
		if name == 'TagPart':
			pos = attrs['Text']
			backref = attrs['Source'][13:-1]
			postext = self.textref.get(backref)
			typeref = self.typeref.get(backref)
			
			self.posHandler(postext, pos, typeref, **self.kwargs)
					
		XMLFilterBase.startElement(self, name, attrs)
		
	
	def endElement(self, name):
		# If we are leaving an instance, clear the backrefs.
		if name == 'Igt':
			self.textref = {}
			
		XMLFilterBase.endElement(self, name)
		
	def posHandler(self, postext, pos, typeref, **kwargs):
		pass

#===============================================================================
# Output the grams
#===============================================================================
class GramOutputFilter(XamlRefActionFilter):
	def __init__(self, upstream, **kwargs):
		XamlRefActionFilter.__init__(self, upstream, **kwargs)
		
		self.tagger_grams_written = False
		self.ltagger_line = False
		
	
	def posHandler(self, postext, pos, typeref, **kwargs):
		# Write out glosses			
		if typeref == 'G':
			if postext and postext.strip():
				write_gram(postext, pos, type='classifier', output=self.kwargs.get('class_out'), **self.kwargs)
				write_gram(postext, pos, type='tagger', output=self.kwargs.get('tag_out'), **self.kwargs)
				
				# And set the state that tagger grams were written
				self.tagger_grams_written = True
				
		elif typeref == 'L':
			write_gram(postext, pos, type='tagger', output=self.kwargs.get('ltag_out'), **self.kwargs)
			self.ltagger_line = True
			
			
					
		
	
	def endElement(self, name):
		# If we are leaving an instance, clear the backrefs.
		if name == 'Igt':
			self.textref = {}
			if self.tagger_grams_written:
				self.tagger_grams_written = False
				self.kwargs.get('tag_out').write('\n')
				self.kwargs.get('tag_out').flush()
				
			if self.ltagger_line:
				self.kwargs.get('ltag_out').write('\n')
				self.kwargs.get('ltag_out').flush()
				self.ltagger_line = False
			
		XMLFilterBase.endElement(self, name)
		
class XMLCleaner(XMLFilterBase):
	def __init__(self, upstream):
		XMLFilterBase.__init__(self, upstream)
		
	def startElement(self, name, attrs):
		newAttrs = {}
		for attr in attrs.keys():
			newAttrs[attr] = unescape(attrs[attr])

		XMLFilterBase.startElement(self, name, newAttrs)
		
class XMLWriter(XMLFilterBase):
	def __init__(self, upstream, fp):
		XMLFilterBase.__init__(self, upstream)
		self._cont_handler = XMLGenerator(open(fp, 'w'), encoding='utf-8')
		
class LGTFilter(XMLFilterBase):
	'''
	Class that filters out IGT instances based on certain
	qualifications:
	
	1)  If they do not contain corruption
	2)  If they contain L, G, and T lines
	3)  No more than 3 instances per DocID.
	'''
	
	def __init__(self, upstream):
		XMLFilterBase.__init__(self, upstream)
		
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
				
		#=======================================================================
		# 
		#=======================================================================
		if self.in_igt:
			self.queue.append(lambda: self._cont_handler.startElement(name, attrs))
		else:
			self._cont_handler.startElement(name, attrs)
		
		
		
	def characters(self, content):
		self.queue.append(lambda: self._cont_handler.characters(content))
		
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
				self._cont_handler.endElement(name)

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
			self.queue.append(lambda: self._cont_handler.endElement(name))
			
		#=======================================================================
		# Process as normal if we are not inside an IGT element.
		#=======================================================================
		elif not self.in_igt:
			self._cont_handler.endElement(name)
			
		
			
	
		
	