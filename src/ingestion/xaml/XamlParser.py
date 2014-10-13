'''
Created on Apr 30, 2014

@author: rgeorgi
'''

import sys, os, re
import xml.sax
from xml.sax.saxutils import XMLFilterBase, XMLGenerator, unescape
from collections import defaultdict
import logging
from alignment.Alignment import AlignedSent, Alignment, AlignedCorpus
from eval.AlignEval import AlignEval
from utils.argutils import ArgPasser, existsfile
from interfaces.stanford_tagger import StanfordPOSTagger
import utils.token
from corpora.IGTCorpus import IGTInstance, IGTTier, Span
from igt.grams import write_gram
from eval.ProjectEval import ProjectEval

MODULE_LOGGER = logging.getLogger(__name__)
ALIGN_LOGGER = logging.getLogger('alignment')


#===============================================================================
# 
#===============================================================================

class XamlParser(object):
	def __init__(self, **kwargs):
		
		kwargs['tag_f'] = open(kwargs.get('tag_out'), 'a', encoding='utf-8')
		kwargs['class_f'] = open(kwargs.get('class_out'), 'a', encoding='utf-8')
		
		#===========================================================================
		# POS Tagger Model 
		#===========================================================================
		
		self.tagger = None
		if kwargs.get('tagger_model'):
			self.tagger = StanfordPOSTagger(kwargs.get('tagger_model'))
	
	#===========================================================================
	# Do the parsing of the XML
	#===========================================================================
	
	def parse(self, fp, **kwargs):
		# Cast as an argpasser for convenience
		kwargs = ArgPasser(kwargs)
		
		# Initialize a base SAX parser
		parser = xml.sax.make_parser()
		
		# Add the current file name to the arguments.
		kwargs['cur_file'] = fp
		
		# Pass the tagger in the arguments if we have one.
		kwargs['stanford_tagger'] = self.tagger
		
		# Original filename
		prefix = os.path.splitext(fp)[0]
		
		outdir = kwargs.get('outdir')
		
		#=======================================================================
		# For each of the separate language files, create their own POS tagged
		# entries for testing.
		#=======================================================================
		ltagger_output = os.path.join(outdir, os.path.basename(prefix)+'_tagger.txt')
		kwargs['ltag_out'] = ltagger_output
		
				
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
		
		# 5) Provide counts of various features about the data.
		output_handler = InstanceCounterFilter(output_handler, **kwargs)
		
		output_handler.parse(fp)



#===============================================================================
# Class for parsing the XAML Text References
#===============================================================================
class XamlRefActionFilter(XMLFilterBase):
	def __init__(self, upstream, **kwargs):
		XMLFilterBase.__init__(self, upstream)
		
		self.textref = {}
		self.typeref = {}
		
		self.kwargs = ArgPasser(kwargs)
		
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
		
		#=======================================================================
		# What has been done to the instance
		#=======================================================================
		self.langTags = False
		self.langSegs = False
		
		self.glossTags = False
		self.glossSegs = False
		
		self.transTags = False
		self.transSegs = False
		
		
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

			tiertype = self.typeref[backref][0]
			
			# The actual text of the segment
			text = attrs['Text']

			# Strip the spaces from inside a token if asked...			
			strip = self.kwargs.get('strip', True, bool)
			text = re.sub('\s*', '', text) if strip else text

			
			self.partnum += 1
			
			s = Span(int(attrs['FromChar']), int(attrs['ToChar']))
			
			t = utils.token.GoldTagPOSToken(text, index=self.partnum, span=s)
			
			self.textref[uid] = t
			self.typeref[uid] = tiertype
			
			# Call the segment handler -----------------------------------------
			self.segHandler(t, tiertype, **self.kwargs)
			
		# ((( POS TIER )))
		
		if name == 'TagPart':
			pos = attrs['Text']
			backref = attrs['Source'][13:-1]
			token = self.textref.get(backref)
			
			# Only try to deal with a tagging if it refers back to a valid element. 			
			if token:
				token.goldlabel = pos
				
				typeref = self.typeref.get(backref)
				
				self.posHandler(token, typeref, **self.kwargs)
					
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
		
		self.langSegs = False
		self.langTags = False
		
		self.glossSegs = False
		self.glossTags = False
		
		self.transSegs = False
		self.transTags = False
		
		self.cur_aln = Alignment()
		self.gt_aln = Alignment()
		self.lg_aln = Alignment()
		
	#===========================================================================
	#  EXTENDED HANDLERS
	#===========================================================================
		
	def alnHandler(self, aln, src_type, tgt_type):
		if src_type == 'G' and tgt_type == 'T':
			self.gt_aln = aln
		elif src_type == 'L' and tgt_type == 'G':
			self.lg_aln = aln
		else:
			MODULE_LOGGER.warn('Unexpected alignment type: "%s-%s" found.' % (src_type, tgt_type))
		
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
		if typeref == 'G':
			self.glossSegs = True
		elif typeref == 'L':
			self.langSegs = True
		elif typeref == 'T':
			self.transSegs = True
		
		
	def posHandler(self, postoken, typeref, **kwargs):
		if typeref == 'G':
			self.glossTags = True
		elif typeref == 'L':
			self.langTags = True
		elif typeref == 'T':
			self.transTags = True
		

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
		
		# Count of average tags per type
		self.counts['gloss_types'] = defaultdict(int)
		self.counts['lang_types'] = defaultdict(int)
		self.counts['trans_types'] = defaultdict(int)
		
		
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

		# For every key listed here, print out a CSV.		
		keys = ['docids', 'annotated_docids', 'instances', 'tagged_instances', 'lang_tags', 'lang_types', 'gloss_tags', 'gloss_types', 'trans_tags', 'trans_types']
		for i, key in enumerate(keys):
			
			# Set the print termination character
			end = ',' if i < len(keys)-1 else '\n'
			
			# If we are looking at types, we should calculate
			# both the raw number of types, and the average tags
			# per type
			if 'types' in key:
				tag_type_count = 0
				for word in self.counts[key]:
					tag_type_count += self.counts[key][word]
				
				avg_tag_per_type = tag_type_count / len(self.counts[key]) if tag_type_count != 0 else 0.0
				
				# First print the count, then the avg
				print(len(self.counts[key]), end=',')
				print(tag_type_count, end=end)
				
			# If the count is not an int, give its length
			# instead of its integer value.
			elif type(self.counts[key]) != int:
				print(len(self.counts[key]), end=end)
			else:				
				print(self.counts[key],end=end)
		
	def posHandler(self, postoken, typeref, **kwargs):
		if typeref == 'G':
			self.counts['gloss_tags'] += 1
			self.counts['gloss_types'][postoken.seq.lower()] += 1	
		elif typeref == 'L':
			self.counts['lang_tags'] += 1
			self.counts['lang_types'][postoken.seq.lower()] += 1
		elif typeref == 'T':
			self.counts['trans_tags'] += 1
			self.counts['trans_types'][postoken.seq.lower()] += 1
			
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
		elif typeref == 'T':
			self.counts['trans_tokens'] += 1			
			
			
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
		
		self.projection_acc = {'match':0,'total':0}
		
		# Create an aligned corpus to compare alignments...
		self.heur_aln_corpus = AlignedCorpus()
		self.gold_aln_corpus = AlignedCorpus()
		
		#=======================================================================
		# Open the language-specific tagger output for writing.
		#=======================================================================
		if self.kwargs.get('ltag_out'):
			ltag_out = open(self.kwargs.get('ltag_out'), 'w', encoding='utf-8')
			
		# And set it to the variables
		self.ltag_out = ltag_out
		
		#=======================================================================
		# Here are the queued portions to write out
		#=======================================================================
		self.gloss_queue = utils.token.Tokenization()
		self.lang_queue = utils.token.Tokenization()
		self.trans_queue = utils.token.Tokenization()
		
	
	def posHandler(self, postoken, typeref, **kwargs):		
		pass
			
			
	def segHandler(self, seg, typeref, **kwargs):
		
		self.isSegmented = True
		
		postext = seg.seq
			
		if typeref == 'G':
			if postext and postext.strip():
				self.gloss_queue.append(seg)				
				
		elif typeref == 'L':
			if postext and postext.strip():
				self.lang_queue.append(seg)
				
		elif typeref == 'T':
			if postext and postext.strip():
				self.trans_queue.append(seg)	
				
		XamlRefActionFilter.segHandler(self, seg, typeref, **kwargs)
		
		
	
	#===========================================================================
	# When an IGT Instance ENDS
	#===========================================================================
	def endIGT(self):
		
		#=======================================================================
		# POS Tag the translation line
		#=======================================================================
		tagged_trans = None
		if self.transSegs:
			#text = ' '.join([t.seq for t in self.trans_segs])
			
			# If the stanford tagger is defined, use it for POS tags instead.
			if self.kwargs.get('stanford_tagger'):
				tagger = self.kwargs.get('stanford_tagger')
				MODULE_LOGGER.debug('Tagging "%s"' % self.trans_queue.text())
				tagged_sent = tagger.tag_tokenization(self.trans_queue, **self.kwargs)
				
				# Assign the 
				for i, token in enumerate(tagged_sent):
					self.trans_queue[i].taglabel = token.label
				
			
				
		#===================================================================
		# Create an IGT instance
		#===================================================================
		
		heur_aln = None
		if self.langSegs and self.glossSegs and self.transSegs:
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
			MODULE_LOGGER.debug('Adding alignment for %s' % trans.text())
			
			heur_aln_sent = AlignedSent(gloss, trans, heur_aln.aln)
			gold_aln_sent = AlignedSent(gloss, trans, self.gt_aln)
			
			self.gold_aln_corpus.append(gold_aln_sent)
			self.heur_aln_corpus.append(heur_aln_sent)
			
			#===================================================================
			# Which alignment type to use; the manual one (gold) or the 
			# automatic one (heur)
			#===================================================================
			if self.kwargs.get('feat_align_type', 'heur') == 'gold':
				heur_aln = gold_aln_sent
		
		
		#===================================================================
		# Write out the gloss tags ---
		#===================================================================
		if self.glossSegs:
			
			# Write out the gloss line ---------------------------------------
			for i, token in enumerate(self.gloss_queue):
				
				aln_labels = []
				#===========================================================
				# Grab pos tags from the translation tags if possible ---
				#===========================================================
				if heur_aln:
					tgts = heur_aln.src_to_tgt(i+1)
					
					# Switch between gold or tagged POS tags -------------------
					
					if self.kwargs.get('feat_align_tags', 'tags') == 'gold':
						l = lambda t: t.goldlabel
					else:
						l = lambda t: t.taglabel
						
					# Now get the alignment labels of the correct type
					aln_labels = [l(self.trans_queue[tgt-1]) for tgt in tgts]

				prev_gram = None
				if i-1 >= 0:
					prev_gram = self.gloss_queue[i-1]
				
				next_gram = None
				if i+1 < len(self.gloss_queue):
					next_gram = self.gloss_queue[i+1]
										
				write_gram(token, output=self.kwargs['class_f'], aln_labels=aln_labels, prev_gram=prev_gram, next_gram=next_gram, type='classifier', **self.kwargs)
				write_gram(token, output=self.kwargs['tag_f'], type='tagger', **self.kwargs)
			
			self.kwargs.get('tag_f').write('\n')
			
		# Write out lang line tags ---------------------------------------------

		if self.lang_queue:
			for token in self.lang_queue:
				# Skip "X" tags
				if token.goldlabel != 'X':
					write_gram(token, output=self.ltag_out, type='tagger', **self.kwargs)
			self.ltag_out.write('\n')
			
		# Reset the counters ---------------------------------------------------
			
		self.gloss_queue = utils.token.Tokenization()
		self.lang_queue = utils.token.Tokenization()
		self.trans_queue = utils.token.Tokenization()
		
		# Parent Call ----------------------------------------------------------
					
		XamlRefActionFilter.endIGT(self)
		
	def endDocument(self):
		ae = AlignEval(self.heur_aln_corpus, self.gold_aln_corpus)
		pe_gold = ProjectEval(self.gold_aln_corpus, 'GOLD_ALN')
		pe_heur = ProjectEval(self.heur_aln_corpus, 'HEUR_ALN')
		pe_gold.eval()
		pe_heur.eval()
		
		ALIGN_LOGGER.info(ae.all())
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
	
	def __init__(self, upstream, **kwargs):
		XMLFilterBase.__init__(self, upstream)
		
		self.valtest = True
		
		# Queue Variables 
		self.queue = []
		self.tiers = set([])
		
		self.last_docid = None
		self.cur_docid = None
		self.cur_docid_count = 0
		
		self.skip = False
		
		self.in_igt = False
		
		# Set the maximum number of instances per docID
		self.docid_limit = kwargs.get('docid_limit', 3)
	
	
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
			# Limit the number of allowed instances per docid to the docid_limit
			# (defaults to 3)
			#===================================================================
			if self.cur_docid_count >= self.docid_limit:
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
			
		
			
	
		
	