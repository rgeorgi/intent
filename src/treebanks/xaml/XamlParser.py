'''
Created on Apr 30, 2014

@author: rgeorgi
'''

from xml.dom import minidom
from utils.xmlutils import get_child_tags, find_tag, getIntAttr, get_ref
import sys
from utils.Token import Tokenization, Token, morpheme_tokenizer, tokenize_string,\
	POSToken
from corpora.IGTCorpus import IGTTier, IGTToken, Span, IGTInstance
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
		
		outdir = kwargs.get('outdir')
		ltagger_output = os.path.join(outdir, os.path.basename(prefix)+'_tagger.txt')
		kwargs['ltag_out'] = open(ltagger_output, 'w')
		
				
		#=======================================================================
		#  FILTERING AND WRITING
		#=======================================================================
		
		
		# 1) Filter out the instances for annotation.
		output_handler = LGTFilter(parser)
		
		# 2) Output the gram information for classifiers and taggers.
		output_handler = GramOutputFilter(output_handler, **kwargs)
		
		# 3) Clean the XML of escape characters.
		output_handler = XMLCleaner(output_handler)
		
		# 4) Write the XML output to file.
		#output_handler = XMLWriter(output_handler, prefix+'-filtered.xml')
		
		output_handler = InstanceCounterFilter(output_handler)
		
		output_handler.parse(fp)

def write_gram(token, **kwargs):
	type = kwargs.get('type')
	output = kwargs.get('output', sys.stdout)
	
	# Previous tag info
	prev_gram = kwargs.get('prev_gram')
	next_gram = kwargs.get('next_gram')
	
	# Get heuristic alignment
	aln_labels = kwargs.get('aln_labels', [])

	#===========================================================================
	# Break apart the token...
	#===========================================================================
	gram = token.seq
	pos = token.label

	# Lowercase if asked for	
	lower = kwargs.get('lowercase', True)
	gram = gram.lower() if gram else gram
		
	# Strip if asked for
	strip = kwargs.get('strip', True)
	gram = re.sub('\s*', '', gram) if strip else gram
	
	# Output the grams for a classifier
	if type == 'classifier':
		output.write(pos)
		
		# Get the morphemes
		morphs = tokenize_string(gram, morpheme_tokenizer)
		
		#=======================================================================
		# Is there a number
		#=======================================================================
		if re.search('[0-9]', gram) and False:
			output.write('\thas-number:1')
			
		#=======================================================================
		# What labels is it aligned with
		#=======================================================================
		if False:
			for aln_label in aln_labels:
				output.write('\taln-label-%s:1' % aln_label)
			
		#=======================================================================
		# Suffix
		#=======================================================================
		if True:
			output.write('\tgram-suffix-%s:1' % gram[-3:])
			
		#=======================================================================
		# Prefix
		#=======================================================================
		if True:
			output.write('\tgram-prefix-%s:1' % gram[:3].replace(':','-'))
			
		#=======================================================================
		# Number of morphs
		#=======================================================================		
		if False:
			output.write('\t%d-morphs:1' % len(morphs))
		
		#=======================================================================
		# Add previous gram features
		#=======================================================================
		if kwargs.get('context-feats', True):
			
			#===================================================================
			# Previous gram
			#===================================================================
			if prev_gram and True:
				prev_gram = prev_gram.seq
				prev_gram = prev_gram.lower() if lower else prev_gram
				prev_gram = re.sub('\s*', '', prev_gram) if strip else prev_gram
						
				# And then tokenize...
				for token in tokenize_string(prev_gram, morpheme_tokenizer):
					output.write('\tprev-gram-%s:1' % token.seq)
					
			#===================================================================
			# Next gram
			#===================================================================
			if next_gram and False:
				next_gram = next_gram.seq
				next_gram = next_gram.lower() if lower else next_gram
				next_gram = re.sub('\s*', '', next_gram) if strip else next_gram
				
				for token in tokenize_string(next_gram, morpheme_tokenizer):
					output.write('\tnext-gram-%s:1' % token.seq)
		

		
		for token in morphs:
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
		
		#=======================================================================
		# Segment Tier States
		#=======================================================================
		self.partnum = 0
		
		# Alignment Counters
		self.in_alnpart = False
		self.alnsrc = None
		self.aln_parts = []
		
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
			
			self.partnum += 1
			
			s = Span(int(attrs['FromChar']), int(attrs['ToChar']))
			
			t = POSToken(text, index=self.partnum, span=s)
			
			self.textref[uid] = t
			self.typeref[uid] = type
			
			self.segHandler(t, type, **self.kwargs)
			
		# POS Tier
		if name == 'TagPart':
			pos = attrs['Text']
			backref = attrs['Source'][13:-1]
			postoken = self.textref.get(backref)
			
			if postoken:
				postoken.label = pos
				
				typeref = self.typeref.get(backref)
				
				self.posHandler(postoken, typeref, **self.kwargs)
					
		if name == 'AlignPart':
			a_src = attrs['Source'][13:-1]			
			self.alnsrc = a_src
		
		if name == 'x:Reference':
			self.in_alnpart = True
					
		XMLFilterBase.startElement(self, name, attrs)
		
	def characters(self, content):
		if self.in_alnpart:
			self.aln_parts.append(content)
		
		XMLFilterBase.characters(self, content)
	
	def endElement(self, name):
		# If we are leaving an instance, clear the backrefs.
		if name == 'Igt':
			self.textref = {}
			
		if name == 'SegTier':
			self.partnum = 0
			
		if name == 'AlignPart':
			self.alnHandler(self.alnsrc, self.aln_parts)
			self.aln_parts = []
			self.alnsrc = None
			
		if name == 'x:Reference':
			self.in_alnpart = False
			
		XMLFilterBase.endElement(self, name)
		
	def alnHandler(self, src, tgts):
		srcRep = self.textref.get(src)
		if srcRep:
			pass
			
		for tgt in tgts:
			tgtRep = self.textref.get(tgt)
			if tgtRep:
				pass
		
		
	def segHandler(self, seg, typeref, **kwargs):
		pass
		
	def posHandler(self, postoken, typeref, **kwargs):
		pass

#===============================================================================
# Count various things
#===============================================================================

class InstanceCounterFilter(XamlRefActionFilter):
	
	def __init__(self, parent=None):
		self.instances = 0
		self.gloss_tokens = 0
		self.gloss_tags = 0
		self.lang_tokens = 0
		self.lang_tags = 0
		XMLFilterBase.__init__(self, parent=parent)
		
	def endElement(self, name):
		XamlRefActionFilter.endElement(self, name)
		
	def endDocument(self):
		print(self.instances)
		XMLFilterBase.endDocument(self)

#===============================================================================
# Output the grams
#===============================================================================
class GramOutputFilter(XamlRefActionFilter):
	def __init__(self, upstream, **kwargs):
		XamlRefActionFilter.__init__(self, upstream, **kwargs)
		
		self.tagger_grams_written = False
		self.ltagger_line = False
		
		self.gloss_queue = []
		self.lang_queue = []
		self.trans_queue = []
		
	
	def posHandler(self, postoken, typeref, **kwargs):
		
		postext = postoken.seq
			
		if typeref == 'G':
			if postext and postext.strip():
				self.gloss_queue.append(postoken)				
				
		elif typeref == 'L':
			if postext and postext.strip():
				self.lang_queue.append(postoken)
				
		elif typeref == 'T':
			if postext and postext.strip():
				self.trans_queue.append(postoken)	
			
			
	def segHandler(self, postoken, typeref, **kwargs):
		pass
		
		
		
	
	def endElement(self, name):
		# If we are leaving an instance, clear the backrefs.
		if name == 'Igt':
			self.textref = {}
			
			#===================================================================
			# Create an IGT instance
			#===================================================================
			
			heur_aln = None
			if self.lang_queue and self.gloss_queue and self.trans_queue:
				i = IGTInstance()
				
				# Create lang tier
				lang = IGTTier(seq=self.lang_queue, kind='lang')
				i.append(lang)
				
				gloss = IGTTier(seq=self.gloss_queue, kind='gloss')
				i.append(gloss)
				
				trans = IGTTier(seq=self.trans_queue, kind='trans')
				i.append(trans)
				
				heur_aln = i.gloss_heuristic_alignment()
				
			
			
			#===================================================================
			# Write out the gloss tags
			#===================================================================
			if self.gloss_queue:
				
				# Write out the gloss line
				for i, postoken in enumerate(self.gloss_queue):
					
					aln_labels = []
					#===========================================================
					# Grab pos tags from the translation tags if possible
					#===========================================================
					if heur_aln:
						tgts = heur_aln.src_to_tgt(i+1)
						aln_labels = [self.trans_queue[tgt-1].label for tgt in tgts]

							
					
					prev_gram = None
					if i-1 >= 0:
						prev_gram = self.gloss_queue[i-1]
					
					next_gram = None
					if i+1 < len(self.gloss_queue):
						next_gram = self.gloss_queue[i+1]
						
					
					
					write_gram(postoken, output=self.kwargs.get('class_out'), aln_labels=aln_labels, prev_gram=prev_gram, next_gram=next_gram, type='classifier', **self.kwargs)
					write_gram(postoken, output=self.kwargs.get('tag_out'), type='tagger', **self.kwargs)
				
				self.kwargs.get('tag_out').write('\n')
				
			#===================================================================
			# Write out the lang line tags
			#===================================================================
			if self.lang_queue:
				for postoken in self.lang_queue:
					write_gram(postoken, output=self.kwargs.get('ltag_out'), type='tagger', **self.kwargs)
				self.kwargs.get('ltag_out').write('\n')
				
			self.gloss_queue = []
			self.lang_queue = []
			self.trans_queue = []
					
		XamlRefActionFilter.endElement(self, name)
		
#===============================================================================
# Do some cleaning of the XML elements.
#===============================================================================
class XMLCleaner(XMLFilterBase):
	def __init__(self, upstream):
		XMLFilterBase.__init__(self, upstream)
		
	def startElement(self, name, attrs):
		newAttrs = {}
		for attr in attrs.keys():
			newAttrs[attr] = unescape(attrs[attr])

		XMLFilterBase.startElement(self, name, newAttrs)
		
		
#===============================================================================
# Write the XML out to a file.
#===============================================================================
class XMLWriter(XMLFilterBase):
	def __init__(self, upstream, fp):
		XMLFilterBase.__init__(self, upstream)
		self._cont_handler = XMLGenerator(open(fp, 'w'), encoding='utf-8')
		
		
#===============================================================================
# The filter that selects which instances are useful.
#===============================================================================
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
			
		
			
	
		
	