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
from utils.argutils import ArgPasser
from interfaces.stanford_tagger import StanfordPOSTagger
import utils.token
from corpora.IGTCorpus import IGTInstance, IGTTier, Span, IGTCorpus
from igt.grams import write_gram
from eval.ProjectEval import ProjectEval
from xml.sax.expatreader import ExpatParser

# Xigt Imports

from igt.rgxigt import RGIgt, RGItem, RGTier, RGCorpus, RGMetadata
from interfaces.mallet_maxent import MalletMaxent

MODULE_LOGGER = logging.getLogger(__name__)
ALIGN_LOGGER = logging.getLogger('alignment')
CLASS_LOGGER = logging.getLogger('classification')


class StatefulSAX(ExpatParser):
	'''
	This subclasses the default ExpatParser
	in order to keep global state for variables.
	This way, filters can be stacked and 
	still reference what came before
	'''
	def __init__(self):
		ExpatParser.__init__(self)
		self.vars = {}
		
	def __setitem__(self, k, v):
		self.vars[k] = v
		
	def __getitem__(self, k):
		return self.vars[k]
	
	def __delitem__(self, k):
		del self.vars[k]
		
	def get(self, k, default=None):
		if k in self.vars:
			return self[k]
		else:
			return default
		
		
class InheritingXMLFilterBase(XMLFilterBase):
	
	def __init__(self, upstream, **kwargs):
				
		if hasattr(upstream, '_stateholder'):
			self._stateholder = upstream._stateholder
		else:
			self._stateholder = upstream
			
		XMLFilterBase.__init__(self, upstream)
		
		
	
	@property
	def stateholder(self):
		return self._stateholder
	
#===============================================================================
# 
#===============================================================================


class XamlProcessor(object):
	'''
	Abstract class to process XAML documents as requested
	'''
	
	def __init__(self, **kwargs):
		self.parser = StatefulSAX()
		self.handler = self.parser
		self.kwargs = kwargs
		self.files = []
		
	def add_lgt_filter(self):
		self.handler = LGTFilter(self.handler, **self.kwargs)
		
	def add_file(self, path):
		self.files.append(path)
		
		
	def parse(self, fp):
		self.handler.parse(fp)
		
	def parse_all(self):
		for f in self.files:
			self.parse(f)
		
	def add_gram_output_filter(self, gram_path):
		
		# Open up the specified gram path for writing...
		f = open(gram_path, 'a', encoding='utf-8')
		self.kwargs['class_f'] = f
		
		self.handler = GramOutputFilter(self.handler, **self.kwargs)
		
	def add_igt_corpus_filter(self):
		self.handler = IgtCorpusBuilderFilter(self.handler, **self.kwargs)
		
	def __getitem__(self, k):
		return self.parser.__getitem__(k)
		
		
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
		parser = StatefulSAX()
		
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
		
		# Build the igt corpus, and keep info on the current
		# instance for downstream filters...
		output_handler = IgtCorpusBuilderFilter(output_handler, **kwargs)
		
		output_handler = XigtBuilderFilter(output_handler, **kwargs)
		
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
class XamlRefActionFilter(InheritingXMLFilterBase):
	def __init__(self, upstream, **kwargs):
		InheritingXMLFilterBase.__init__(self, upstream)
		
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
			
			# Store the raw text in the global state for
			# later...
			self.stateholder['cur_raw'] = attrs['Text']
			
			
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
			
		if name == 'IgtCorpus':
			self.endCorpus()
			
		XMLFilterBase.endElement(self, name)
		
	#===========================================================================
	# END CORPUS
	#===========================================================================
	def endCorpus(self):
		pass
	
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
# Build Xigt Instances
#===============================================================================

class XigtBuilderFilter(InheritingXMLFilterBase):
	
	def startElement(self, name, attrs):		
		InheritingXMLFilterBase.startElement(self, name, attrs)
		
		if name == 'IgtCorpus':
			self.stateholder['cur_corpus'] = RGCorpus()
			
		#=======================================================================
		# IGT Instances
		#=======================================================================
		elif name == 'Igt':
			
			# Add the language to the metadata
			meta = RGMetadata()
			#langmeta = RGMeta('language', content=attrs['Language'])
			#meta.content=langmeta
			
			
			# Create a Xigt IGT instance
			#igtid = '%s-%s' % (attrs['DocId'],attrs['FromLine'])
			igtid = self.stateholder['cur_corpus'].askIgtId()
			inst = RGIgt(id=igtid, metadata=meta)
			

			
			self.stateholder['cur_xigt'] = inst

			# Create default tiers and add them
			# to the instance...
			txttier = RGTier('%s-txt' % igtid, type='odin-raw', igt=inst)			
						
			inst.add_list([txttier])
			
		#=======================================================================
		# Text Tiers
		#=======================================================================
		elif name == 'TextTier' and attrs.get('TierType') != 'odin-txt' and 'Text' in attrs:
			
			# Grab the current instance
			inst = self.stateholder['cur_xigt']
			
			# Grab the text tier...
			tt = inst.getTier('odin-raw')[0]
			
			# Create a container item, where the ID is the 
			# automatically created ID with LGT+LineNo
			txtitem = RGItem(id=attrs['TierType'], content=attrs['Text'], tier=tt, type='odin-raw')
			
			# Set its UUID attribute to the 'Name' field.
			txtitem.attributes['uuid'] = attrs['Name']

			tt.add(txtitem)
			
		#=======================================================================
		# Segmentation Tier
		#=======================================================================
		elif name == 'SegTier':
			# Generate a new ID for this tier based on the 
			newId = self.stateholder['cur_xigt'].askTierId('words')
						
			# Initialize a segmentation tier...
			segtier = RGTier(id=newId, type='words')
			segtier.attributes['uuid'] = attrs['Name']
			self.stateholder['cur_seg_tier'] = segtier
			
		#=======================================================================
		# Segmentation Parts
		#=======================================================================
		elif name == 'SegPart':
			
			srcuuid = attrs['SourceTier'][13:-1]
			src_obj = self.stateholder['cur_xigt'].findUUID(srcuuid)
				
			segtier = self.stateholder['cur_seg_tier']
				
			
			# Now create the segmentation item.
			segitem = RGItem(type='seg-token', content=attrs['Text'], id=segtier.askItemId())
			
			# Add the reference to what this segmentation is referring to 
			segitem.attributes['content'] = '%s[%s:%s]' % (src_obj.id, attrs['FromChar'], attrs['ToChar'])
			
			# Add this item's index
			segitem.attributes['index'] = segtier.askIndex()
			
			# Also add our own UUID to the mix
			segitem.attributes['uuid'] = attrs['Name']
			
			# If we are in a mergepart...
			if self.stateholder.get('cur_mergepart'):
				self.stateholder['cur_mergerefs'].append(segitem)
			else:
				# Add it to the tier
				segtier.add(segitem)
			

				
			
		#=======================================================================
		# POSTagTier
		#=======================================================================
		elif name == 'PosTagTier':
			inst = self.stateholder['cur_xigt']
			
			# Grab an ID string from the current instance...
			newId = inst.askTierId('pos')
			
			# Create new postier and store it in memory
			postier = RGTier(id=newId, type='pos')
			self.stateholder['cur_pos_tier'] = postier
			
		#=======================================================================
		# POSTagItem
		#=======================================================================
		elif name == 'TagPart':
			# Get the currents state objects...
			inst = self.stateholder['cur_xigt']			
			postier = self.stateholder['cur_pos_tier']

			# Grab attributes from the XAML
			posuuid = attrs['Name']
			content = attrs['Text']

			# Find the referenced item...						
			srcuuid = attrs['Source'][13:-1]
			src_obj = inst.findUUID(srcuuid)
			
			# Create the new object
			positem = RGItem(id=postier.askItemId(), content=content)
			
			# Add the UUID to the item
			positem.attributes['uuid'] = posuuid
			
			# Add the reference:
			positem.attributes['content'] = src_obj.id
			
			# Now, add to the tier...
			postier.add(positem)
			
		#=======================================================================
		# MergePart
		#=======================================================================
		elif name == 'MergePart':
			self.stateholder['cur_mergepart'] = attrs['Name']
			self.stateholder['cur_mergerefs'] = []
			
		#======================================================================
		# AlignmentTier
		#======================================================================
		elif name == 'AlignmentTier':
			inst = self.stateholder['cur_xigt']
			
			# Get the fresh item ID
			alignid = inst.askTierId('alignment')
			aligntype = attrs['TierType']
			alignuuid = attrs['Name']
			
			# Create the new tier
			aligntier = RGTier(id=alignid, type='alignment')
			aligntier.attributes['uuid'] = alignuuid
			
			# Also add what type of alignment...
			aligntier.attributes['aligntype'] = aligntype
			
			# Store it in state
			self.stateholder['cur_align_tier'] = aligntier
			
		#=======================================================================
		# AlignPart
		#=======================================================================
		elif name == 'AlignPart':
			# Get the source for this alignpart...			
			self.stateholder['cur_align_src'] = attrs['Source'][13:-1]
			
		#=======================================================================
		# x:reference
		# These are the targets of the alignparts... 
		#=======================================================================
			
			
			
			
	
	#===========================================================================
	# END ELEMENT
	#===========================================================================
	def endElement(self, name):
		InheritingXMLFilterBase.endElement(self, name)
		
		#=======================================================================
		# Igt Instance
		#=======================================================================
		if name == 'Igt':
			self.stateholder['cur_corpus'].add(self.stateholder['cur_xigt'])
			
		#=======================================================================
		# Whole Corpus
		#=======================================================================
		elif name == 'IgtCorpus':
			corp = self.stateholder['cur_corpus']
			
			# Remove the UUIDs left over from XAML.
			corp.delUUIDs()
			
			# Dump out the corpus as XIGT 
			#xigt.codecs.xigtxml.dump(open('test.xml', 'w', encoding='utf-8'), corp, pretty_print=True)
			# sys.exit()
			
			
			
			
			
			
			
			
			
		#=======================================================================
		# SegTier
		#=======================================================================
		elif name == 'SegTier':
			self.stateholder['cur_xigt'].add(self.stateholder['cur_seg_tier'])
			
			# Clear our state
			del self.stateholder['cur_seg_tier']
			
		#=======================================================================
		# PosTier
		#=======================================================================
		elif name == 'PosTagTier':
			self.stateholder['cur_xigt'].add(self.stateholder['cur_pos_tier'])
			
			# Clear our state
			del self.stateholder['cur_pos_tier']
			
		#=======================================================================
		# MergePart
		#=======================================================================
		elif name == 'MergePart':
			refstr = '+'.join([m.attributes['content'] for m in self.stateholder['cur_mergerefs']])
			txtstr = ''.join([m.content for m in self.stateholder['cur_mergerefs']])
			
			mrgid = self.stateholder['cur_seg_tier'].askItemId()
			
			mrgitem = RGItem(type='words', content=txtstr, id=mrgid)
			
			# Now set the attributes
			mrgitem.attributes['content'] = refstr
			mrgitem.attributes['uuid'] = self.stateholder['cur_mergepart']
			
			# Get the current segtier and add it.
			self.stateholder['cur_seg_tier'].add(mrgitem)
			
			# Now, reset our state			
			del self.stateholder['cur_mergepart']
			del self.stateholder['cur_mergerefs']
			
		#=======================================================================
		# AlignPart
		#=======================================================================
		elif name == 'AlignPart':
			del self.stateholder['cur_align_src']		
			
			
		#=======================================================================
		# AlignmentTier
		#=======================================================================
		elif name == 'AlignmentTier':
			alntier = self.stateholder['cur_align_tier']
			self.stateholder['cur_xigt'].add(alntier)
			
			# Clear the state
			del self.stateholder['cur_align_tier']
			
	#===========================================================================
	# Characters
	#===========================================================================
	def characters(self, content):
		InheritingXMLFilterBase.characters(self, content)
		
		# If we have a cur_aln_src, that means we are in
		# an alignment part.
		if content.strip() and self.stateholder.get('cur_align_src'):
			inst = self.stateholder.get('cur_xigt')
			alntier = self.stateholder.get('cur_align_tier')
			alnsrc = self.stateholder.get('cur_align_src')
			alntgt = content.strip()
			
			srcobj = inst.findUUID(alnsrc)
			tgtobj = inst.findUUID(alntgt)
			
			if srcobj and tgtobj:
				alnid = alntier.askItemId()
				alnitem = RGItem(id=alnid, type='aln')
				
				# Add the source and target attribtues...
				alnitem.attributes['src'] = srcobj.id
				alnitem.attributes['tgt'] = tgtobj.id
				
				# Add it to the tier...
				alntier.add(alnitem)
			
		

#===============================================================================
# Count various things
#===============================================================================

class InstanceCounterFilter(XamlRefActionFilter):
	
	def __init__(self, upstream, **kwargs):
		XamlRefActionFilter.__init__(self, upstream, **kwargs)
		
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
# This filter will build an IGT corpus and store it in the global parser.
#===============================================================================

class IgtCorpusBuilderFilter(XamlRefActionFilter):
	
	# Initialize, and create a new corpus in memory.
	def __init__(self, upstream, **kwargs):
		XamlRefActionFilter.__init__(self, upstream)
		
		#=======================================================================
		# Here are the queued portions to write out
		#=======================================================================
		self.gloss_queue = utils.token.Tokenization()
		self.lang_queue = utils.token.Tokenization()
		self.trans_queue = utils.token.Tokenization()
		
		self.stateholder['igt_corpus'] = IGTCorpus()
		
	# When starting a new igt instance...
	def igtHandler(self, name, attrs, **kwargs):
		XamlRefActionFilter.igtHandler(self, name, attrs, **kwargs)
		
		
		idstr = '%s-%s-%s' % (attrs['DocId'], attrs['FromLine'], attrs['ToLine'])
		self.stateholder['cur_instance'] = IGTInstance(id=idstr)
		
	def endIGT(self):
		
		# Get the instance from the global scope.
		i = self.stateholder['cur_instance']
		
		# Convert the queues to tiers
		lang = IGTTier(content=self.lang_queue, type='lang')
		i.add(lang)
		
		gloss = IGTTier(content=self.gloss_queue, type='gloss')
		i.add(gloss)
		
		trans = IGTTier(content=self.trans_queue, type='trans')
		i.add(trans)
		
		# Add this instance to the corpus
		self.stateholder['igt_corpus'].add(i)
				
				
		self.gloss_queue = utils.token.Tokenization()
		self.lang_queue = utils.token.Tokenization()
		self.trans_queue = utils.token.Tokenization()
		XamlRefActionFilter.endIGT(self)
		
		
	# Add segments to the various queues...
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
		
	
	def endCorpus(self):
		XamlRefActionFilter.endCorpus(self)
		
		

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
		ltag_out = None
		if self.kwargs.get('ltag_out'):
			ltag_out = open(self.kwargs.get('ltag_out'), 'w', encoding='utf-8')
			
		# And set it to the variables
		self.ltag_out = ltag_out
		
		# Add the classifier stat stuff
		self.stateholder['class_matches'] = 0
		self.stateholder['class_compares'] = 0
		
	
	#===========================================================================
	# When an IGT Instance ENDS
	#===========================================================================
	def endIGT(self):
		
		inst = self.stateholder['cur_instance']
		
		#=======================================================================
		# POS Tag the translation line
		#=======================================================================

		if inst.trans:
			#text = ' '.join([t.seq for t in self.trans_segs])
			
			# If the stanford tagger is defined, use it for POS tags instead.
			if self.kwargs.get('stanford_tagger'):
				tagger = self.kwargs.get('stanford_tagger')
				MODULE_LOGGER.debug('Tagging "%s"' % inst.trans.text())
				tagged_sent = tagger.tag_tokenization(inst.trans, **self.kwargs)
				
				
				# Assign the 
				for i, token in enumerate(tagged_sent):
					inst.trans[i].taglabel = token.label
					

		#===================================================================
		# Get the alignments from the IGT Instance
		#===================================================================
		
		heur_aln = None
		
		if inst.lang and inst.gloss and inst.trans:
			
			
			heur_aln = inst.gloss_heuristic_alignment(**self.kwargs)
			
			# Add debug line
			MODULE_LOGGER.debug('Adding alignment for %s' % inst.trans.text())
			
			heur_aln_sent = AlignedSent(inst.gloss, inst.trans, heur_aln.aln)
			gold_aln_sent = AlignedSent(inst.gloss, inst.trans, self.gt_aln)
			
			
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
			for i, token in enumerate(inst.gloss):
				
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
					aln_labels = [l(inst.trans[tgt-1]) for tgt in tgts]

				prev_gram = None
				if i-1 >= 0:
					prev_gram = inst.gloss[i-1]
				
				next_gram = None
				if i+1 < len(inst.gloss):
					next_gram = inst.gloss[i+1]
										
				write_gram(token, output=self.kwargs['class_f'], aln_labels=aln_labels, prev_gram=prev_gram, next_gram=next_gram, type='classifier', **self.kwargs)
				
				if self.kwargs.get('tag_f'):
					write_gram(token, output=self.kwargs['tag_f'], type='tagger', **self.kwargs)
			
			if self.kwargs.get('tag_f'):
				self.kwargs.get('tag_f').write('\n')
			
		# Write out lang line tags ---------------------------------------------

		if inst.lang:
			for token in inst.lang:
				
				# Skip "JUNK" tags
				if token.goldlabel != 'JUNK' and token.goldlabel != 'X':
					write_gram(token, output=self.ltag_out, type='tagger', **self.kwargs)
			
			if self.ltag_out:
				self.ltag_out.write('\n')
		
		# Compare language line tags to what the classifier produces... --------
		if inst.gloss:
			classifier = self.kwargs.get('classifier')
			
			self.kwargs['prev_gram'] = None
			self.kwargs['next_gram'] = None
			
			for i, g_token in enumerate(inst.gloss):
				
				# Set the previous/next grams based on our current position...
				if i+1 < len(inst.gloss):
					self.kwargs['next_gram'] = inst.gloss[i+1]
				if i-1 > 0:
					self.kwargs['prev_gram'] = inst.gloss[i-1]
				
				
				tag = classifier.classify_token(g_token, **self.kwargs).largest()[0]
				
				if tag == g_token.goldlabel:
					self.stateholder['class_matches'] += 1
				
				self.stateholder['class_compares'] += 1
				
			# Now clear these arguments...
			del self.kwargs['prev_gram']
			del self.kwargs['next_gram']

				
			
		
		# Parent Call ----------------------------------------------------------
					
		XamlRefActionFilter.endIGT(self)
		
	def endDocument(self):
		ae = AlignEval(self.heur_aln_corpus, self.gold_aln_corpus)
		pe_gold = ProjectEval(self.gold_aln_corpus, 'GOLD_ALN')
		pe_heur = ProjectEval(self.heur_aln_corpus, 'HEUR_ALN')
		pe_gold.eval()
		pe_heur.eval()
		
		ALIGN_LOGGER.info(ae.all())
		CLASS_LOGGER.info('%d,%d' % (self.stateholder['class_matches'],self.stateholder['class_compares']))
		XamlRefActionFilter.endDocument(self)
		
#===============================================================================
# Do some cleaning of the XML elements.
#===============================================================================
class XMLCleaner(InheritingXMLFilterBase):
	def __init__(self, upstream, **kwargs):
		InheritingXMLFilterBase.__init__(self, upstream)
		
				
	def startElement(self, name, attrs):
		newAttrs = {}
		for attr in attrs.keys():
			newAttrs[attr] = unescape(attrs[attr])

		XMLFilterBase.startElement(self, name, newAttrs)
		

#===============================================================================
# Write the XML out to a file.
#===============================================================================
class XMLWriter(InheritingXMLFilterBase):
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
class LGTFilter(InheritingXMLFilterBase):
	'''
	Class that filters out IGT instances based on certain
	qualifications:
	
	1)  If they do not contain corruption
	2)  If they contain L, G, and T lines
	3)  No more than 3 instances per DocID.
	'''
	
	def __init__(self, upstream, **kwargs):
		InheritingXMLFilterBase.__init__(self, upstream)
		
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
		self.docid_limit = kwargs.get('docid_limit', None)
		
	
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
			if self.docid_limit and self.cur_docid_count >= self.docid_limit:
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
			
		
			
	
		
	