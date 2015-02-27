'''
Created on Feb 25, 2015

@author: rgeorgi
'''

#===============================================================================
# Logging
#===============================================================================
import logging
from igt.rgxigtutils import strip_enrichment, follow_alignment
from alignment.Alignment import AlignedCorpus, AlignedSent
from eval.AlignEval import AlignEval
import glob
import os
logging.basicConfig(handlers=[logging.StreamHandler()])
XAML_LOG = logging.getLogger(__name__)
XAML_LOG.setLevel(logging.DEBUG)

#  -----------------------------------------------------------------------------

import lxml.etree
import sys
from igt.rgxigt import RGCorpus, RGTier, rgp, RGIgt, RGItem, RGWordTier, RGWord,\
	RGBilingualAlignmentTier, RGTokenTier, RGToken
import re
from utils.uniqify import uniqify
import logging


#===============================================================================
# Other
#===============================================================================
class XamlParseException(Exception): pass

#===============================================================================
# POS Tag
#===============================================================================

def pos(pos_tier, inst):
	sources = [xaml_ref(r) for r in pos_tier.xpath(".//*[local-name()='TagPart']/@Source")]
	source_tiers = uniqify([inst.find(r).tier.id for r in sources if inst.find(r)])
	
	if len(source_tiers) > 1:
		raise XamlParseException('POS Tag Tier references more than one tier...')
	
	source_tier = inst.find(source_tiers[0])
	
	if source_tier.type == 'words':
		pid = 'w-pos'
	elif source_tier.type == 'translation-words':
		pid = 'tw-pos'
	elif source_tier.type == 'gloss-words':
		pid = 'gw-pos'
	
	pt = RGTokenTier(id=pid, igt=inst, alignment=source_tier.id, type='pos')
	
	for tagpart in pos_tier.findall('.//{*}TagPart'):
		src = xaml_ref(tagpart.attrib['Source'])
		txt = tagpart.attrib['Text']
		
		pos_t = RGToken(id=pt.askItemId(), alignment=src, text=txt, tier=pos_tier)
		pt.add(pos_t)
	inst.add(pt)
		
		

#===============================================================================
# Alignment tools
#===============================================================================

def get_refs(e):
	return [xaml_ref(r) for r in e.xpath(".//*[local-name()='Reference']/text()")]

def get_alignments(aln_tier, reverse=True):
	pairs = []
	
	for aln_part in aln_tier.findall('.//{*}AlignPart'):
		
		src_id = xaml_ref(aln_part.attrib['Source'])
		tgt_ids = get_refs(aln_part)
		for tgt_id in tgt_ids:
			pairs.append((src_id, tgt_id))
			
	if reverse:
		return [(y, x) for x, y in pairs]
	else:
		return pairs
		

	

def align(aln_tier, inst):
	# Figure out what the source alignment is:
	tgt_id = xaml_ref(aln_tier.attrib['AlignWith'])
	
	tgt_tier = inst.find(tgt_id)
	
	# Find all the references contained by tokens inside here....
	refs = aln_tier.xpath(".//*[local-name()='AlignPart']/@Source")
	
	# Rewrite the reference...
	refs = [xaml_ref(r) for r in refs]
	
	# Now find them
	refs = uniqify([inst.find(r).tier.id for r in refs if inst.find(r)])
	
	if len(refs) > 1:
		raise XamlParseException('Alignment tier aligns with multiple other tiers.')
	
	src_tier = inst.find(refs[0])
	

	
	# If we are aligning gloss words and translation words, we need to make a bilingual alignment tier.
	# otherwise, we should just place the alignment attribute on the words.
	bilingual = False
	reverse = False
	
	if src_tier.type == 'gloss-words' and tgt_tier.type == 'translation-words':
		bilingual = True
		reverse = True
	elif src_tier.type == 'translation-words' and tgt_tier.type == 'gloss-words':
		bilingual = True
	elif src_tier.type == 'gloss-words' and tgt_tier.type == 'words':
		pass
	elif src_tier.type == 'words' and tgt_tier.type == 'gloss-words':
		reverse = True
		
	else:
		#print(src_tier.id)
		XAML_LOG.warning("Unknown alignment type: %s - %s" % (src_tier.type, tgt_tier.type))
		#raise XamlParseException("Unknown alignment type: %s - %s" % (src_tier.type, tgt_tier.type))
		
	aln_pairs = get_alignments(aln_tier, reverse)
	
	#===========================================================================
	# If reversed, swap things around...
	#===========================================================================
	if reverse:
		temp_tier = src_tier
		src_tier = tgt_tier
		tgt_tier = temp_tier
		
	#===========================================================================
	# Do the bilingual alignment.
	#===========================================================================
		
	if bilingual:
		at = RGBilingualAlignmentTier(id=inst.askTierId('bilingual-alignments','a'), source=src_tier.id, target=tgt_tier.id)
		for src, tgt in aln_pairs:
			at.add_pair(src, tgt)
			
		inst.add(at)
		
	# Otherwise, we want to just add the alignment attribute to a words tier.
	else:
		
		src_tier.alignment = tgt_tier.id

		for src, tgt in aln_pairs:
			
			src_w = src_tier.find(src)
			if src_w:
				src_w.alignment = tgt
			else:
				XAML_LOG.warn('Src token %s not found.' % src)
			

def replace_references(inst, old_id, new_id):
	for item in inst.findall(attributes={'alignment':old_id}):
		item.alignment = new_id
	for item in inst.findall(attributes={'source':old_id}):
		item.attributes['source'] = new_id
	for item in inst.findall(attributes={'target':old_id}):
		item.attributes['target'] = new_id

def conventionify_words(inst, type, letter):
	t = inst.find(type=type)
	old_t_id = t.id
	t.id = letter
	
	replace_references(inst, old_t_id, t.id)
		
	for w in t:
		old_id = w.id
		w.id = letter+str(w.index)
		replace_references(inst, old_id, w.id)

		

def conventionify(inst):
	'''
	Given a xaml-converted instance, replace the xaml-generated IDs with IDs
	fitting the conventions.
	'''
	
	# Starting off, doing the raw tiers.
	for i, line in enumerate(inst.find('r')):
		old_id = line.id
		new_id = line.tier.id+'%s'%line.index
		line.id = new_id
		
		for item in inst.findall(segments=old_id):
			item.segmentation = item.segmentation.replace(old_id, new_id)
		for item in inst.findall(contents=old_id):
			item.content = item.content.replace(old_id, new_id)
		
			
	# Next, let's do the words tiers.
	conventionify_words(inst, 'words', 'w')
	conventionify_words(inst, 'translation-words', 'tw')
	conventionify_words(inst, 'gloss-words', 'gw')
	
	inst.refresh_index()
		
	
			
# -------------------

def xaml_id(e):
	return 'xaml'+e.attrib['Name'].replace('_','')

xaml_ref_re = re.compile('_([\S]+?)}?$')
def xaml_ref(s):
	return 'xaml'+re.search(xaml_ref_re, s).group(1)

def load(xaml_path):
	# Load up the document and get the root
	# element
	xc = RGCorpus()
	
	xaml = lxml.etree.parse(xaml_path)
	root = xaml.getroot()
	
	# The default namespace doesn't get a prefix
	# for some reason, so put that into the dictionary.
	# Now, let's start by grabbin all the IGT instances
	for igt in root.findall('.//{*}Igt'):
		
		# Create the new IGT Instance...
		inst = RGIgt(id=xaml_id(igt))
		
		# Create the raw tier...
		tt = RGTier(id='r', type='odin', attributes={'state':'raw'}, igt=inst)
		
		# Next, let's gather the text tiers that are not the full raw text tier.
		lines = igt.xpath(".//*[local-name()='TextTier' and not(contains(@TierType,'odin-txt'))]")
		for textitem in lines:
			
			# Occasionally some broken lines have no text.
			if 'Text' in textitem.attrib:
			
				tags = re.search('([^\-]+)\-?', textitem.attrib['TierType']).group(1)
				
				item = RGItem(id=xaml_id(textitem), attributes={'tag':tags})
				item.text = textitem.attrib['Text']
				tt.add(item)
			
		# Add the text tier to the instance.
		inst.add(tt)
			
		#=======================================================================
		# Segmentation Tiers. ---
		#=======================================================================
		# Now, we start on the segmentation tiers.
		segtiers = igt.findall('.//{*}SegTier')		
		for segtier in segtiers:
			
			# First, we need to figure out what previous
			# tier this one is segmenting.
			sources = uniqify(segtier.xpath('.//@SourceTier'))
			
			if len(sources) > 1:
				raise XamlParseException('Multiple sources for segmentation line.')
			
			# Otherwise, find that tier.
			segmented_tier = inst.find(id=xaml_ref(sources[0]))
			
			# Now, decide what type of tier we are creating based on the tag of the referenced tier.
			seg_type = None
			
			tags = segmented_tier.attributes['tag']
			
			if 'L' in tags:
				seg_type = 'words'
			elif 'G' in tags:
				seg_type = 'gloss-words'
			elif 'T' in tags:
				seg_type = 'translation-words'
			else:
				raise XamlParseException('Unknown tag type in segmentation tier.')
			
			# Create the new words tier.
			wt = RGWordTier(id=xaml_id(segtier), type=seg_type, igt=inst, segmentation='r')
			
			# Now, add the segmentation parts.
			for segpart in segtier.findall('.//{*}SegPart'):
				
				ref_expr = '%s[%s:%s]' % (segmented_tier.id, segpart.attrib['FromChar'], segpart.attrib['ToChar'])
				
				w = RGWord(id=xaml_id(segpart), 
						segmentation=ref_expr)
				
				wt.add(w)
		
			inst.add(wt)
			

			
		#=======================================================================
		# Alignment Tiers
		#=======================================================================
		aln_tiers = igt.findall('.//{*}AlignmentTier')
		for aln_tier in aln_tiers:
			align(aln_tier, inst)
			
					
		#=======================================================================
		# Finally, for POS tiers.
		#=======================================================================
		pos_tiers = igt.findall('.//{*}PosTagTier')
		for pos_tier in pos_tiers:
			pos(pos_tier, inst)
		
		xc.add(inst)
	return xc
		

if __name__ == '__main__':
	for path in glob.glob('/Users/rgeorgi/Documents/treebanks/xigt_odin/annotated/*-filtered.xml'):
		
		lang = os.path.basename(path)[0:4]
		
		xc = load(path)
		
			
		new_xc = xc.copy()
		new_xc.giza_align_t_g()
		
		gold_ac = AlignedCorpus()
		
		heur_ac = AlignedCorpus()
		giza_ac = AlignedCorpus()
		
		for old_inst, new_inst in zip(xc, new_xc):
			# Strip any enrichment (pos tags, bilingual alignment)
			# from the instance we are going to try the tools on.
			
			
			# TODO: This assertion error is sloppy, find another way.
			try:
				ba = old_inst.get_trans_gloss_alignment()
			except AssertionError:
				continue
			if ba:
				new_inst.heur_align()
				
				heur_sent = AlignedSent(new_inst.trans.tokens(), new_inst.gloss.tokens(), new_inst.get_trans_gloss_alignment('intent-heuristic'))
				giza_sent = AlignedSent(new_inst.trans.tokens(), new_inst.gloss.tokens(), new_inst.get_trans_gloss_alignment('intent-giza'))
				gold_sent = AlignedSent(new_inst.trans.tokens(), new_inst.gloss.tokens(), old_inst.get_trans_gloss_alignment())
				
				heur_ac.append(heur_sent)
				giza_ac.append(giza_sent)
				gold_ac.append(gold_sent)
				
		giza_ae = AlignEval(giza_ac, gold_ac)
		heur_ae = AlignEval(heur_ac, gold_ac)
		
		print(lang)
		print(heur_ae.all())
		print(giza_ae.all())
			

	
	