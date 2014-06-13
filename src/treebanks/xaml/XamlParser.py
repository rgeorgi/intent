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
from _collections import defaultdict
import logging
from alignment.Alignment import AlignedSent, Alignment, AlignedCorpus
from eval.AlignEval import AlignEval


		
class XamlParser(object):
	def __init__(self, **kwargs):
		kwargs['tag_f'] = open(kwargs.get('tag_out'), 'a')
		kwargs['class_f'] = open(kwargs.get('class_out'), 'a')
		
	
	def parse(self, fp, **kwargs):
		parser = xml.sax.make_parser()
		
		kwargs['cur_file'] = fp
		
		# Original filename
		prefix = os.path.splitext(fp)[0]
		
		outdir = kwargs.get('outdir')
		ltagger_output = os.path.join(outdir, os.path.basename(prefix)+'_tagger.txt')
		kwargs['ltag_out'] = ltagger_output
		
		#=======================================================================
		# Get the output file
		#=======================================================================
		
				
		#=======================================================================
		#  FILTERING AND WRITING
		#=======================================================================
		
		
		# 1) Filter out the instances for annotation.
		output_handler = parser
		output_handler = LGTFilter(output_handler)
		
		# 2) Output the gram information for classifiers and taggers.
		output_handler = GramOutputFilter(output_handler, **kwargs)
		
		# 3) Clean the XML of escape characters.
		output_handler = XMLCleaner(output_handler, **kwargs)
		
		# 4) Write the XML output to file.
# 		output_handler = XMLWriter(output_handler, os.path.join(outdir, os.path.basename(prefix))+'-filtered.xml')
		
		output_handler = InstanceCounterFilter(output_handler, **kwargs)
		
		output_handler.parse(fp)

def write_gram(token, **kwargs):
	type = kwargs.get('type')
	output = kwargs.get('output', sys.stdout)
	
	posdict = kwargs.get('posdict')
		
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
		
		#=======================================================================
		# Get the morphemes
		#=======================================================================
		morphs = tokenize_string(gram, morpheme_tokenizer)
		
		#=======================================================================
		# Is there a number
		#=======================================================================
		if re.search('[0-9]', gram) and False:
			output.write('\thas-number:1')
			
		#=======================================================================
		# What labels is it aligned with
		#=======================================================================
		if True:
			for aln_label in aln_labels:
				output.write('\taln-label-%s:1' % aln_label)
			
		#=======================================================================
		# Suffix
		#=======================================================================
		if False:
			output.write('\tgram-suffix-3-%s:1' % gram[-3:].replace(':','-'))
			output.write('\tgram-suffix-2-%s:1' % gram[-2:].replace(':','-'))
			output.write('\tgram-suffix-1-%s:1' % gram[-3:].replace(':','-'))
			
		#=======================================================================
		# Prefix
		#=======================================================================
		if False:
			output.write('\tgram-prefix-3-%s:1' % gram[:3].replace(':','-'))
			output.write('\tgram-prefix-2-%s:1' % gram[:2].replace(':','-'))
			output.write('\tgram-prefix-1-%s:1' % gram[:1].replace(':','-'))
			
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
		
		#=======================================================================
		# Iterate through the morphs
		#=======================================================================
		
		for token in morphs:
			#===================================================================
			# Just write the morph
			#===================================================================
			output.write('\t%s:1' % token.seq)
			
			#===================================================================
			# If the morph resembles a word in our dictionary, give it
			# a predicted tag
			#===================================================================
			if token.seq in posdict and True:
				
				top_tags = posdict.top_n(token.seq)
				best = top_tags[0][0]
				if best != pos:
					logging.debug('%s TAGGED as %s NOT %s' % (gram, pos, best))
				
				output.write('\ttop-dict-word-%s:1' % top_tags[0][0])
				if len(top_tags) > 1:
					output.write('\tnext-dict-word-%s:1' % top_tags[1][0])
				

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
		
		self.alnsrc_type = None
		self.alntgt_type = None
		
		# This will contain the current alignment
		self.cur_aln = Alignment()
		
		self.lg_aln = None
		self.gt_aln = None
		
		
	#===========================================================================
	# Start Element
	#===========================================================================
	
	def startElement(self, name, attrs):
		
		# ((( TEXT )))
		
		if name == 'TextTier' and attrs.get('Text'):
			uid = attrs['Name']
			self.textref[uid] = attrs['Text']
			self.typeref[uid] = attrs['TierType']
			
		if name == 'Igt':
			self.igtHandler(name, attrs, **self.kwargs)
			
		# ((( SEGMENTATION )))
		
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
			
		# ((( POS TIER )))
		
		if name == 'TagPart':
			pos = attrs['Text']
			backref = attrs['Source'][13:-1]
			postoken = self.textref.get(backref)
			
			if postoken:
				postoken.label = pos
				
				typeref = self.typeref.get(backref)
				
				self.posHandler(postoken, typeref, **self.kwargs)
					
		# ((( ALIGNMENT )))
		
		if name == 'AlignPart':
			a_src = attrs['Source'][13:-1]			
			self.alnsrc = a_src
		
		if name == 'AlignPart.AlignedParts':
			self.in_alnpart = True
			
		# ((( Parent Handler )))					
		XMLFilterBase.startElement(self, name, attrs)
		
	#===========================================================================
	#  Characters
	#===========================================================================
	def characters(self, content):
		# If the characters are alignment references, add them.
		if self.in_alnpart:
			self.aln_parts.append(content)
		
		XMLFilterBase.characters(self, content)
	
	
	#===========================================================================
	# endElement
	#===========================================================================
	def endElement(self, name):
		# If we are leaving an instance, clear the backrefs.
		if name == 'Igt':
			self.endIGT()
			
		if name == 'SegTier':
			self.partnum = 0
			
		if name == 'AlignPart':
			self.alnPartHandler(self.alnsrc, self.aln_parts)
			self.aln_parts = []
			self.alnsrc = None
			
		if name == 'AlignmentTier':
			self.alnHandler(self.cur_aln, self.alnsrc_type, self.alntgt_type)
			self.alnsrc_type = None
			self.alntgt_type = None
			self.cur_aln = Alignment()
			
		if name == 'AlignPart.AlignedParts':
			# When we exit the aligned parts
			self.in_alnpart = False
			
		XMLFilterBase.endElement(self, name)
		
	#===========================================================================
	# STANDARD HANDLERS
	#===========================================================================
	
	def endIGT(self):
		self.textref = {}
		
	#===========================================================================
	#  EXTENDED HANDLERS
	#===========================================================================
		
	def alnHandler(self, aln, src_type, tgt_type):
		if src_type == 'G' and tgt_type == 'T':
			self.gt_aln = aln
		elif src_type == 'L' and tgt_type == 'G':
			self.lg_aln = aln
		else:
			logging.warn('Unexpected alignment type: "%s-%s" found.' % (src_type, tgt_type))
		
	def alnPartHandler(self, src, tgts):
		srcRep = self.textref.get(src)
		srcType = self.typeref.get(src)
		
		# Only continue on if we have a valid reference to go with.
		if srcRep:
			self.alnsrc_type = srcType
			
			# Now, iterate through the targets
			for tgt in tgts:
				tgtRep = self.textref.get(tgt)
				tgtType = self.typeref.get(tgt)
				
				# Only look at this target if we have a valid reference
				if tgtRep:
					self.alntgt_type = tgtType
					self.cur_aln.add((srcRep.index, tgtRep.index))
					
		
	def igtHandler(self, name, attrs, **kwargs):
		pass
		
	def segHandler(self, seg, typeref, **kwargs):
		pass
		
	def posHandler(self, postoken, typeref, **kwargs):
		pass

#===============================================================================
# Count various things
#===============================================================================

class InstanceCounterFilter(XamlRefActionFilter):
	
	def __init__(self, upstream, **kwargs):
		self.cur_file = kwargs.get('cur_file')
		
		#=======================================================================
		# Last tagged or segmented counters
		#=======================================================================
		self.was_tagged = {}
		self.was_segmented = {}
		#  ---------------------------------------------------------------------
		
		self.counts = defaultdict(int)
		self.counts['docids'] = defaultdict(int)
		self.counts['annotated_docids'] = defaultdict(int)
		
		
		XamlRefActionFilter.__init__(self, upstream, **kwargs)
	
	#===========================================================================
	# EndElement
	#===========================================================================
		
	def endElement(self, name):
		#=======================================================================
		# Print the output at the document end
		#=======================================================================
		if name == 'IgtCorpus':
			self.countprinter()
			
		if name == 'Igt':
			self.counts['instances'] += 1
			self.counts['tagged_instances'] += 1 if self.was_tagged else 0
			self.counts['segmented_instances'] += 1 if self.was_segmented else 0
			
			if self.was_tagged:
				self.counts['annotated_docids'][self.cur_docid] += 1
			self.counts['docids'][self.cur_docid] += 1
			
			self.was_tagged = {}
			self.was_segmented = {}			

			
		XamlRefActionFilter.endElement(self, name)
		
	
		
	def countprinter(self):
		print(os.path.basename(self.cur_file), end='\t')
		print(len(self.counts['docids'].keys()), end=',')
		print(len(self.counts['annotated_docids'].keys()), end=',')
		
		keys = ['instances','segmented_instances', 'tagged_instances', 'lang_tokens', 'gloss_tokens', 'lang_tags', 'gloss_tags']
		for i, key in enumerate(keys):
			print(self.counts[key],end=',' if i < len(keys)-1 else '\n')
		
	def posHandler(self, postoken, typeref, **kwargs):
		if typeref == 'G':
			self.counts['gloss_tags'] += 1			
		elif typeref == 'L':
			self.counts['lang_tags'] += 1
			
		# Add what type of this was tagged.
		self.was_tagged[typeref] = True
			
		XamlRefActionFilter.posHandler(self, postoken, typeref, **kwargs)
		
	# Handle new igt instances...
	def igtHandler(self, name, attrs, **kwargs):
		docid = attrs['DocId']
		self.cur_docid = docid
		
		XamlRefActionFilter.igtHandler(self, name, attrs, **kwargs)
		
	def segHandler(self, seg, typeref, **kwargs):
		if typeref == 'G':
			self.counts['gloss_tokens'] += 1
		elif typeref == 'L':
			self.counts['lang_tokens'] += 1
			
		self.was_segmented[typeref] = True
		
		XamlRefActionFilter.segHandler(self, seg, typeref, **kwargs)
		


#===============================================================================
# Output the grams
#===============================================================================
class GramOutputFilter(XamlRefActionFilter):
	def __init__(self, upstream, **kwargs):
		XamlRefActionFilter.__init__(self, upstream, **kwargs)
		
		self.tagger_grams_written = False
		self.ltagger_line = False
		
		
		# Create an aligned corpus to compare alignments...
		self.heur_aln_corpus = AlignedCorpus()
		self.gold_aln_corpus = AlignedCorpus()
		
		#=======================================================================
		# Open the language-specific tagger output for writing.
		#=======================================================================
		if self.kwargs.get('ltag_out'):
			ltag_out = open(self.kwargs.get('ltag_out'), 'w')
			
		# And set it to the variables
		self.ltag_out = ltag_out
		
		#=======================================================================
		# Here are the queued portions to write out
		#=======================================================================
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
		
		
	
	#===========================================================================
	# When an IGT Instance ENDS
	#===========================================================================
	def endIGT(self):
		
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
			
			
			# Add debug line
			logging.debug('Adding alignment for %s' % trans.text())
			
			heur_aln_sent = AlignedSent(gloss, trans, heur_aln.aln)
			gold_aln_sent = AlignedSent(gloss, trans, self.gt_aln)
			
			self.gold_aln_corpus.append(gold_aln_sent)
			self.heur_aln_corpus.append(heur_aln_sent)
			
			
		
		
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
					
				write_gram(postoken, output=self.kwargs['class_f'], aln_labels=aln_labels, prev_gram=prev_gram, next_gram=next_gram, type='classifier', **self.kwargs)
				write_gram(postoken, output=self.kwargs['tag_f'], type='tagger', **self.kwargs)
			
			self.kwargs.get('tag_f').write('\n')
			
		#===================================================================
		# Write out the lang line tags
		#===================================================================
		if self.lang_queue:
			for postoken in self.lang_queue:
				# Skip "X" tags
				if postoken.label != 'X':
					write_gram(postoken, output=self.ltag_out, type='tagger', **self.kwargs)
			self.ltag_out.write('\n')
			
		self.gloss_queue = []
		self.lang_queue = []
		self.trans_queue = []
					
		XamlRefActionFilter.endIGT(self)
		
	def endDocument(self):
		ae = AlignEval(self.heur_aln_corpus, self.gold_aln_corpus)
		print(ae.all())
		XamlRefActionFilter.endDocument(self)
		
#===============================================================================
# Do some cleaning of the XML elements.
#===============================================================================
class XMLCleaner(XMLFilterBase):
	def __init__(self, upstream, **kwargs):
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
	'''
	Class to simply output the current XML to a file.
	'''
	def __init__(self, upstream, fp):
		XMLFilterBase.__init__(self, upstream)
		self.output = XMLGenerator(open(fp, 'w'), encoding='utf-8')
		
	def startDocument(self):
		self.output.startDocument()
		XMLFilterBase.startDocument(self)
		
	def startElement(self, name, attrs):
		self.output.startElement(name, attrs)
		XMLFilterBase.startElement(self, name, attrs)
		
	def characters(self, content):
		self.output.characters(content)
		XMLFilterBase.characters(self, content)
		
	def endDocument(self):
		self.output.endDocument()
		XMLFilterBase.endDocument(self)
		
	def endElement(self, name):
		self.output.endElement(name)
		XMLFilterBase.endElement(self, name)
		
	def processingInstruction(self, target, data):
		self.output.processingInstruction(target, data)
		XMLFilterBase.processingInstruction(self, target, data)
		
		
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
			
		
			
	
		
	