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
	
	def parse(self, xamldoc):
		# Keep some counters:
		instances = set()
		seg_count = 0
		pos_counts = 0
		doc_ids = set()
		
		tag_f = open('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/gloss_tags.txt', 'a')
		
		# Get the root element of the document
		m = minidom.parse(xamldoc)
		
		# Get the corpus element and then the item container
		corp = get_child_tags(m, 'IgtCorpus')[0]
		items = get_child_tags(corp, 'IgtCorpus.Items')[0]
		
		# Now, get each IGT instance.
		instances = get_child_tags(items, 'Igt')
		for instance in instances:
			docid = instance.getAttribute('DocId')
			lang = instance.getAttribute('Language')
			name = instance.getAttribute('name')
			
			#print(lang, docid)
			
			# ===== Create the Wrapper object for the instance
			x = XAMLData()
			x.docid = docid
			x.name = name
			# =======================
			
			
			# Get root tier element
			tier_element = get_child_tags(instance, 'Igt.Tiers')[0]
			
			#===================================================================
			# TEXT TIERS
			#===================================================================
			text_tiers = get_child_tags(tier_element, 'TextTier')
			
			ref_dict = {}
			
			for text_tier in text_tiers:
				tname = text_tier.getAttribute('Name')
				ttext = text_tier.getAttribute('Text')
				ttype = text_tier.getAttribute('TierType')
				
				# Enter the text tier into the tier dict
				ref_dict[tname] = XAMLElement(tname, ttext, type=ttype)
				
			#===================================================================
			# COMPOUND Tiers
			#===================================================================
			compound_tiers = get_child_tags(tier_element, 'CompoundTextTier')
			for compound_tier in compound_tiers:
				cttype = compound_tier.getAttribute('TierType')
				ctname = compound_tier.getAttribute('Name')
				lines = find_tag(compound_tier, 'Reference')
				ref_dict[ctname] = XAMLElement(ctname, '', type=cttype)
			
			#===================================================================
			#  SEGMENTATION TIERS
			#===================================================================


			seg_tiers = get_child_tags(tier_element, 'SegTier')
			for seg_tier in seg_tiers:
				
				#===============================================================
				# Seg Parts....
				#===============================================================
				seg_parts = find_tag(seg_tier, 'SegPart|MergePart', max_depth=2)
				# if we don't have any seg parts, skip:
				if not seg_parts:
					continue
				
	
				
				#===============================================================
				# Let's make this an IGT Tier...
				#===============================================================
				t = IGTTier()
				ttype = seg_tier.getAttribute('TierType')					
				if ttype.startswith('L'):
					t.kind = 'lang'
					x.lang = t
				elif ttype.startswith('G'):
					t.kind = 'gloss'
					x.gloss = t
				elif ttype.startswith('T'):
					t.kind = 'trans'
					x.trans = t
					
				
				
				#===============================================================
				# Now, add the tokens to it.
				#===============================================================
				
				for i, seg_part in enumerate(seg_parts):
					sname = seg_part.getAttribute('Name')
					stext = seg_part.getAttribute('Text')
					
					seg_ref = get_ref(seg_part, 'SourceTier')
					if seg_ref:
						seg_source = ref_dict[get_ref(seg_part, 'SourceTier')]
						seg_type = seg_source.type
					else:
						seg_type = None
					
					
					fchar = getIntAttr(seg_part, 'FromChar')
					tchar = getIntAttr(seg_part, 'ToChar')

					
					# Now get the token:					
					token = IGTToken(stext, span=Span(fchar, tchar), index=i+1)
					t.append(token)
					
					ref_dict[sname] = XAMLElement(sname, stext, seg_type)
									
			
			if x.has_segs():
				seg_count += 1
				doc_ids.add(docid)
			
					
			#===================================================================
			# POS Tagged Tier
			#===================================================================
			pos_tag_tiers = get_child_tags(tier_element, 'PosTagTier')
			tag_parts = find_tag(tier_element, 'TagPart')
			
			# POS tags
			
			source_type = None
			
			pos_tags = []
			tokens = []
			
			for tag_part in tag_parts:
				
				source = get_ref(tag_part, 'Source')
				if not source_type and source:
					source_type = ref_dict[source].type
					
				#===============================================================
				# Dump out the tokens for classification
				#===============================================================
				
				pos = tag_part.getAttribute('Text')
				text = ref_dict[source].text
				
				pos_tags.append(pos)
				tokens.append(text)
	
			if source_type and source_type.startswith('G'):
				for tag, token in zip(pos_tags, tokens):

# 					tag_f.write('%s/%s '%(token,tag))
					
					token_str = re.sub('\s', '', token)
					tag_f.write('%s/%s '%(token_str,tag))
					
					# UNCOMMENT BELOW FOR CLASSIFER
# 					tag_f.write(tag)
# 					pos_counts += 1
# 					for token in tokenize_string(token, tokenizer=morpheme_tokenizer):						
# 						tag_f.write('\t'+token.seq.lower()+':1')
# 						token_str = token.seq.lower()
# 						token_str = re.sub('\s', '', token_str)
# 						tag_f.write('%s/%s '%(token_str,tag))
# 					tag_f.write('\n')					
				
				tag_f.write('\n')
								
				
				
			#===================================================================
			# ALIGNMENT TIERS
			#===================================================================
			
			aln_tiers = get_child_tags(tier_element, 'AlignmentTier')
			for aln_tier in aln_tiers:				
				# Aligned pairs
				aln_parts = get_child_tags(get_child_tags(aln_tier, 'AlignmentTier.Parts')[0], 'AlignPart')
				for aln_part in aln_parts:
					
					aln_src = aln_part.getAttribute('Source')[13:-1]
					
					# If there are no aligned parts, the word is unaligned.
					aln_tgts = get_child_tags(aln_part, 'AlignPart.AlignedParts')
					
					# Otherwise, it is aligned
					if aln_tgts:
						aln_tgts = get_child_tags(aln_tgts[0], 'Reference')
					
					# Get the source text
					aln_txt = aln_part.getAttribute('Text')
										
					# Get the aligned references
					for aln_tgt in aln_tgts:
						aln_ref = aln_tgt.childNodes[0].data						
						tgt_txt = ref_dict[aln_ref].text
					
					
		print(lang, seg_count, len(doc_ids), pos_counts)
			

		
		