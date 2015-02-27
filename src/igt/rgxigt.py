'''
Subclassing of the xigt package to add a few convenience methods.


'''

#===============================================================================
# Logging
#===============================================================================

import logging
import sys
from interfaces.mallet_maxent import MalletMaxent
import pickle
from interfaces.stanford_tagger import StanfordPOSTagger
logging.basicConfig(handlers=[logging.NullHandler()])
PARSELOG = logging.getLogger(__name__)


#  -----------------------------------------------------------------------------

import xigt.core
from xigt.core import Metadata, Meta, Tier, Item, Igt,\
	get_alignment_expression_ids, XigtCorpus
import re
from xigt.codecs import xigtxml
from unittest.case import TestCase
from uuid import uuid4
from xigt.codecs.xigtxml import encode_tier, encode_item, encode_igt, encode_xigtcorpus
from igt.igtutils import merge_lines, clean_lang_string, clean_gloss_string,\
	clean_trans_string, remove_hyphens, surrounding_quotes_and_parens, punc_re

import utils.token
from collections import defaultdict
import interfaces.giza
from utils.setup_env import c
from alignment.Alignment import Alignment, heur_alignments
from utils.token import Token, POSToken
import copy
from interfaces.giza import GizaAligner


#===============================================================================
# Commonly Used Strings ---
#===============================================================================

# Words ------------------------------------------------------------------------

trans_words = 'translation-words'
gloss_words = 'gloss-words'
lang_words = 'words'

trans_word_id = 'tw'
gloss_word_id = 'gw'
lang_word_id = 'w'

# Phrases ----------------------------------------------------------------------

trans_phrase = 'translations'
lang_phrase  = 'phrases'


#===============================================================================
# Exceptions
#===============================================================================

class RGXigtException(Exception):
	pass

class NoODINRawException(RGXigtException):
	pass 

class TextParseException(RGXigtException):
	pass

class NoLangLineException(TextParseException):
	pass

class NoGlossLineException(TextParseException):
	pass

class NoTransLineException(TextParseException):
	pass

class GlossLangAlignException(RGXigtException):
	pass

#===============================================================================
# Mixins
#===============================================================================

class FindMixin():
	'''
	Extension of the recursive search for non-iterable elements.
	'''
	
	def find_self(self, id=None, attributes=None, type = None, segments = None, contents=None):
		'''
		Check on this element to see if it matches the find criteria. Must satisfy all the specified
		criteria, (they are considered unspecified if "None")
		
		:param id:
		:type id:
		:param attributes:
		:type attributes:
		:param type:
		:type type:
		:param segments:
		:type segments:
		'''
		
		id_match = id is None or (self.id == id)
		type_match = type is None or (self.type == type)
		attr_match = attributes is None or (set(attributes.items()).issubset(set(self.attributes.items())))
		seg_match  = segments is None or (hasattr(self, 'segmentation') and segments in get_alignment_expression_ids(self.segmentation))
		
		# TODO: not sure the contents is working...
		cnt_match = contents is None or (hasattr(self, 'content') and contents in get_alignment_expression_ids(self.content))
		
		# At least ONE thing must be specified
		assert any([id, attributes, type, segments, contents])
		
		if id_match and type_match and attr_match and seg_match and cnt_match:
			return self
		else:
			return None
		
	def find(self, id=None, attributes=None, type=None, segments=None, contents=None):
		return self.find_self(id, attributes, type, segments, contents)
	
	def findall(self, id=None, attributes=None, type=None, segments=None, contents=None):
		found = self.find_self(id, attributes, type, segments, contents)
		if found:
			return [found]
		else:
			return []

class RecursiveFindMixin(FindMixin):

	def find(self, id=None, attributes=None, type=None, segments=None, contents=None):
		'''
		Generic find function for non-iterable elements. NOTE: This version stops on the first match.
		
		:param id: id of an element to find, or None to search by attribute.
		:type id: str
		:param attributes: key:value pairs that are an inclusive subset of those found in the desired item.
		:type attributes: dict
		'''
		if self.find_self(id,attributes,type,segments,contents) is not None:
			return self
		else:
			found = None
			for child in self:
				found = child.find(id, attributes, type, segments, contents)
				if found is not None:
					break
			return found
		
	def findall(self, id=None, attributes=None, type=None, segments=None, contents=None):
		'''
		Find function that does not terminate on the first match.
		'''
		if self.find_self(id, attributes, type, segments, contents) is not None:
			return [self]
		else:
			found = []
			for child in self:
				new_found = child.findall(id, attributes, type, segments, contents)
				found.extend(new_found)
			return found
				

		
		
#===============================================================================

class RGCorpus(xigt.core.XigtCorpus, RecursiveFindMixin):
	def delUUIDs(self):
		for i in self.igts:
			i.delUUIDs()
			
	def askIgtId(self):
		return 'i%d' % (len(self.igts)+1)
	
	def __len__(self):
		return len(self._list)
	
	def copy(self, limit=None):
		new_c = RGCorpus(id=self.id, attributes=copy.deepcopy(self.attributes), metadata=copy.copy(self.metadata), igts=None)
		
		for i, igt in enumerate(self.igts):
			new_c.add(igt.copy(parent=new_c))
			
			if limit and i >= limit:
				break
			
		return new_c
	
	@classmethod
	def from_txt(cls, path, require_trans = False, require_gloss = False, require_lang = False, require_1_to_1 = True):
		'''
		Read in a odin-style textfile to create the xigt corpus.
		 
		:param path: Path to the text file
		:type path: str
		'''
		# Initialize the corpus
		xc = cls()
		
		# Open the textfile and read the contents...
		f = open(path, 'r', encoding='utf-8')
		data = f.read()
		
		# Replace invalid characters...
		_illegal_xml_chars_RE = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')
		data = re.sub(_illegal_xml_chars_RE, ' ', data)
		
		
		f.close()
		
		# Read all the text lines
		inst_txts = re.findall('doc_id=[\s\S]+?\n\n', data)
		
		#=======================================================================
		# Begin parsing...
		#=======================================================================
		
		parsed = 0
		PARSELOG.info('Beginning parse on "%s"' % path)
		for inst_txt in inst_txts:
			
			if parsed % 250 == 0:
				PARSELOG.info('Parsing instance %d...' % parsed)
				pass
			
			# Handle the requirement for 1_to_1 alignment.
			try:
				i = RGIgt.fromString(inst_txt, corpus=xc, require_1_to_1=require_1_to_1)
			except GlossLangAlignException as glae:
				PARSELOG.info(glae)
				if require_1_to_1:
					continue
				else:
					pass
							
			
			# Try to get the translation line. ---------------------------------
			try:
				hastrans = i.trans
			except NoTransLineException as ntle:
				PARSELOG.info(ntle)
				hastrans = False
				
			# Try to get the gloss line. --------------------------------------
			try:
				hasgloss = i.gloss
			except NoGlossLineException as ngle:
				PARSELOG.info(ngle)
				hasgloss = False
			
			# Try to get the language line. ------------------------------------
			try:
				haslang = i.lang
			except NoLangLineException as nlle:
				PARSELOG.info(nlle)
				haslang = False


			parsed +=1
			
			trans_constraint = (hastrans and require_trans) or (not require_trans)
			gloss_constraint = (hasgloss and require_gloss) or (not require_gloss)
			lang_constraint  = (haslang  and require_lang)  or (not require_lang)
			
			if trans_constraint and gloss_constraint and lang_constraint:
				xc.add(i)
			
			
			
				
			
		# Return the corpus
		return xc
	
	
	@classmethod
	def loads(cls, s):
		xc = xigtxml.loads(s)
		xc.__class__ = RGCorpus
		xc._finish_load()
		return xc
	
	@classmethod
	def load(cls, path):
		xc = xigtxml.load(path)
		xc.__class__ = RGCorpus
		xc._finish_load()
		return xc
	
	def _finish_load(self):
		# Now, convert all the IGT instances to RGIgt instances.
		for igt in self.igts:
			igt.__class__ = RGIgt			
			
			for tier in igt.tiers:
				tier.__class__ = RGTier
				
				for i, item in enumerate(tier):
					item.__class__ = RGItem
					item.index = i+1
				
			igt.enrich_instance()
	
	def filter(self, attr):
		new_igts = []
		for i in self:
			try:
				tier = getattr(i, attr)
			except TextParseException as tpe:
				PARSELOG.info(tpe)
			else:
				new_igts.append(i)
				
		self.igts = new_igts
				
	
	def require_trans_lines(self):
		self.filter('trans')
		
	def require_gloss_lines(self):
		self.filter('gloss')
		
	def require_lang_lines(self):
		self.filter('lang')
		
	def require_one_to_one(self):
		self.require_gloss_lines()
		self.require_lang_lines()
		new_igts = []
		for i in self:
			if len(i.gloss) == len(i.lang):
				new_igts.append(i)
			else:
				PARSELOG.info('Filtered out "%s" because gloss and lang not same length.')
		self.igts = new_igts
			
				
	
	def giza_align_t_g(self, resume = True):
		'''
		Perform giza alignments on the gloss and translation
		lines.
		
		:param resume: Whether to "resume" from the saved aligner, or start fresh.
		:type resume: bool
		'''
		
		# First, make sentences out of the gloss and text lines.
		g_sents = [i.glosses.text().lower() for i in self]
		t_sents = [i.trans.text().lower() for i in self]
		
		
		if resume:
			# Next, load up the saved gloss-trans giza alignment model
			ga = interfaces.giza.GizaAligner.load(c['g_t_prefix'], c['g_path'], c['t_path'])
	
			# ...and use it to align the gloss line to the translation line.
			g_t_asents = ga.force_align(g_sents, t_sents)
			
		# Otherwise, start a fresh alignment model.
		else:
			ga = GizaAligner()
			g_t_asents = ga.temp_train(g_sents, t_sents)
		
		# Before continuing, make sure that we have the same number of alignments as we do instances.
		assert len(g_t_asents) == len(self), 'giza: %s -- self: %s' % (len(g_t_asents), len(self))
		
		# Next, iterate through the aligned sentences and assign their alignments
		# to the instance.
		for g_t_asent, igt in zip(g_t_asents, self):
			t_g_aln = g_t_asent.aln.flip()
			igt.set_bilingual_alignment(igt.trans, igt.glosses, t_g_aln, created_by = 'intent-giza')
			
	def giza_align_l_t(self):
		'''
		Perform giza alignments directly from language to translation lines, for comparison
		
		:rtype: Alignment
		'''
		
		l_sents = [i.lang.text().lower() for i in self]
		t_sents = [i.trans.text().lower() for i in self]
		
		ga = interfaces.giza.GizaAligner()
		
		l_t_asents = ga.temp_train(l_sents, t_sents)
		
		assert len(l_t_asents) == len(self)
		
		for l_t_asent, igt in zip(l_t_asents, self):
			t_l_aln = l_t_asent.aln.flip()
			igt.set_bilingual_alignment(igt.trans, igt.lang, t_l_aln)
		
		
			
	def heur_align(self):
		'''
		Perform heuristic alignment between the gloss and translation.
		'''
		for igt in self:
			try:
				g_heur_aln = igt.heur_align()
			except NoTransLineException as ntle:
				logging.warn(ntle)
		
		
		
	
#===============================================================================
# IGT Class
#===============================================================================

class RGIgt(xigt.core.Igt, RecursiveFindMixin):

	# • Constructors -----------------------------------------------------------

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		
		# Add a default bit of metadata...
		self.metadata = [RGMetadata(type='xigt-meta', 
								text=[RGMeta(type='language', 
											 attributes={'name':'english', 
														'iso-639-3':'eng',
														'tiers':'glosses translations'}
											)])]

		#self.metadata = mdt

	@classmethod
	def fromString(cls, string, corpus = None, require_1_to_1 = True):
		'''
		Method to parse and create an IGT instance from odin-style text.
		'''
		
		# Start by looking for the doc_id, and the line range.
		doc_re = re.search('doc_id=(\S+)\s([0-9]+)\s([0-9]+)\s(.*)\n', string)
		docid, lnstart, lnstop, tagtypes = doc_re.groups()
		
		if corpus:
			id = corpus.askIgtId()
		else:
			id = str(uuid4())
		
		inst = cls(id = id, attributes={'doc-id':docid, 
											'line-range':'%s %s' % (lnstart, lnstop),
											'tag-types':tagtypes})
		
		
		# Now, find all the lines
		lines = re.findall('line=([0-9]+)\stag=(\S+):(.*)\n?', string)
		
		# --- 3) Create a raw tier.
		rt = RGLineTier(id = 'r', type='odin', attributes={'state':'raw'}, igt=inst)
		
		for lineno, linetag, linetxt in lines:
			l = RGLine(id = rt.askItemId(), text=linetxt, attributes={'tag':linetag, 'line':lineno}, tier=rt)
			rt.add(l)
			
		inst.add(rt)
		
		# --- 4) Do the enriching if necessary

		inst.basic_processing(require_1_to_1 = require_1_to_1)
		inst.enrich_instance()
		
		
		return inst

	def copy(self, parent = None): 
		'''
		Perform a custom deepcopy of ourselves.
		'''
		new_i = RGIgt(id = self.id, type=self.type, 
					attributes = copy.deepcopy(self.attributes),
					metadata = copy.copy(self.metadata),
					corpus=parent)
		
		for tier in self.tiers:
			new_i.add(tier.copy(parent=new_i))
			
		return new_i
		

	# • Processing of newly created instances ----------------------------------

	def basic_processing(self, require_1_to_1 = True):
		# Create the clean tier
		self.clean_tier()
		self.normal_tier()
		
		# Create the word and phrase tiers...
		try:
			self.trans
		except TextParseException:
			pass
		
		try:
			self.gloss
		except TextParseException:
			pass
		
		try:
			haslang = self.lang
		except TextParseException:
			haslang = False
		
		# Create the morpheme tiers...
		try:
			hasgloss = self.glosses
		except NoGlossLineException:
			hasgloss = False
		
		try:
			self.morphemes
		except NoLangLineException:
			pass

		# And do word-to-word alignment if it's not already done.
		if hasgloss and haslang and not self.gloss.alignment:
			try:
				self.gloss.word_align(self.lang)
			except GlossLangAlignException as glae:
				PARSELOG.info(glae)
				if require_1_to_1:
					raise glae
				else:
					pass

		
	def enrich_instance(self):
			
		# Finally, do morpheme-to-morpheme alignment between gloss
		# and language if it's not already done...
		if not self.glosses.alignment:
			morph_align(self.glosses, self.morphemes)

	
	def askTierId(self, type, id):
		'''
		Generate a new tierID, based on the number of tiers that already exist for that type.
		'''
		numtiers = len(self.findall(type=type))
		return '%s%d' % (id, numtiers+1)

			
	# • Basic Tier Creation ------------------------------------------------------------
	
	def raw_tier(self):
		'''
		Retrieve the raw ODIN tier, otherwise raise an exception.
		'''
		raw_tier = self.find(id='r')
		if not raw_tier:
			raise NoODINRawException('No raw tier found.')
		else:
			return raw_tier
	
	def clean_tier(self):
		'''
		If the clean odin tier exists, return it. Otherwise, create it.
		'''
		
		# If a clean tier already exists, return it.
		clean_tier = self.find(type='odin', attributes={'state':'clean'})
		if clean_tier:
			return clean_tier
		
		else:
			# Otherwise, we will make our own:
			raw_tier = self.raw_tier()
			
			# Now, create the normalized and clean tiers...
			clean_tier = RGLineTier(id = 'c', type='odin',
									 attributes={'state':'clean', 'alignment':raw_tier.id})

			# Create the clean tier...			
			for raw in raw_tier:
				clean_tier.add(RGLine(id=clean_tier.askItemId(), alignment=raw.id, tier=clean_tier, attributes={'tag':raw.attributes['tag']},
										text=raw.text))
			self.add(clean_tier)
			return clean_tier
			
	def add_normal_line(self, normal_tier, tag, cleaning_func, merge=True):
		'''
		Grab the raw lines and add a normalized line, if one with that tag exists. 
		
		:param tier:
		:type tier:
		:param tag:
		:type tag:
		'''
		raw_tier = self.raw_tier()
		raw_lines = [i for i in raw_tier if tag in i.attributes['tag']]
		
		# If there are raw lines to work with...
		if raw_lines:
			norm_line = RGLine(id=normal_tier.askItemId(), alignment=raw_lines[0].id, tier=normal_tier, attributes={'tag':tag})
			
			# Set the content dependent upon whether we are merging or just taking the first line
			if merge:
				norm_cont = merge_lines([l.get_content() for l in raw_lines])
				
				# Update the alignment if we do merge...
				norm_line.alignment = ','.join([l.id for l in raw_lines])
			else:
				# Otherwise, just take the first line.
				norm_cont = raw_lines[0].get_content()
				
			
			# Finally, clean the content accordingly...
			norm_cont = cleaning_func(norm_cont)
			norm_line.text = norm_cont
			normal_tier.add(norm_line)
	
	# • Word Tier Creation -----------------------------------
			
	def normal_tier(self, merge = True):
			# If a clean tier already exists, return it.
			normal_tier = self.find(type='odin', attributes={'state':'normalized'})
			if normal_tier:
				return normal_tier
			else:
				raw_tier = self.raw_tier()
				clean_tier = self.clean_tier()
				
				normal_tier = RGLineTier(id = 'n', type='odin',
										 attributes={'state':'normalized', 'alignment':clean_tier.id})
				
				self.add_normal_line(normal_tier, 'L', clean_lang_string, merge)
				self.add_normal_line(normal_tier, 'G', clean_gloss_string, merge)
				self.add_normal_line(normal_tier, 'T', clean_trans_string, merge)
				
				self.add(normal_tier)
				return normal_tier
			
	def obtain_phrase_and_words_tiers(self, orig_tag, phrase_name, phrase_letter, words_name, words_letter):
		'''
		Starting with an original "line" from the ODIN text, make it into a XIGT
		phrase tier and segmented words tier.
		
		@param orig_tag:  One of 'T', 'G', or 'L'
		@param phrase_tier: The type of the tier used for the phrase.
		@param phrase_letter: The letter used for the id of the tier.
		@param words_name: The type of the tier used for the words.
		@param words_letter: The letter used for the id of the words tier.
		'''
		

		#if we have the words tier, let's just return it.
		words_tier = self.find(type=words_name)
		if words_tier:
			return words_tier		
			
		else:
			# Make sure we've run the normalization...
			c = self.normal_tier()
			
			# Look for the original tags
			line = None
			
			for raw_line in c:
				if orig_tag in raw_line.attributes['tag']:
					line = raw_line
					break 
	
			# TODO: Verify that we shouldn't be throwing an exception here.
			if not line:
				return None
			
			
			# If we have a raw tier, but not a words tier, let's create the needed
			# tiers beneath.
			else:
				
				# If we are dealing with the glosses, don't create a phrase.
				if words_name == gloss_words:
					words_tier =  create_words_tier(line, words_letter, words_name)
					self.add(words_tier)
					return words_tier
				
				# Otherwise, find or create the phrase tier, and base the 
				# words tier off of that.
				else:

					# -- 1) If the phrase tier already exists, get it.
					phrase_tier = self.find(id = phrase_letter)
					if phrase_tier:
						phrase_tier.__class__ = RGPhraseTier
		
					
					# -- 4) If such a phrase tier does not exist, create it.
					else:
						phrase_tier = create_phrase_tier(line, phrase_letter, phrase_name)
						self.add(phrase_tier)
					
					# Finally, create a words tier based on the phrase tier.
					words_tier = create_words_tier(phrase_tier[0], words_letter, words_name)
					self.add(words_tier)
					
					# And finally, return our words tier.
					
					return words_tier
				
						
	

	@property
	def lang(self):
		lt = self.obtain_phrase_and_words_tiers('L', 'phrases', 'p', 'words', 'w')
		if not lt:
			raise NoLangLineException('No lang line available for igt "%s"' % self.id)
		else:
			return lt
		
	@property
	def gloss(self):
		gt = self.obtain_phrase_and_words_tiers('G', 'gloss-phrases', 'g', 'gloss-words', 'gw')
		if not gt:
			raise NoGlossLineException('No gloss line available for igt "%s"' % self.id)
		else:
			return gt
		

	# • Properties -------------------------------------------------------------

		
	@property
	def glosses(self):
		glosses = self.find(type='glosses')
		if glosses:
			glosses.__class__ = RGMorphTier
			return glosses
		else:
			gt = self.gloss.morph_tier('glosses', 'gm')
			self.add(gt)
			return gt
	
	@property
	def morphemes(self):
		morphemes = [t for t in self if t.type == 'morphemes']
		if morphemes:
			morphemes[0].__class__ = RGMorphTier
			return morphemes[0]
		else:
			mt = self.lang.morph_tier('morphemes', 'm')
			self.add(mt)
			return mt
		

	@property
	def trans(self):
		tt = self.obtain_phrase_and_words_tiers('T', trans_phrase, 't', trans_words, trans_word_id)		
		if not tt:
			raise NoTransLineException('No trans line available for igt "%s"' % self.id)
		else:
			return tt
		
	# • Alignment --------------------------------------------------------------

		
	def get_trans_gloss_alignment(self):
		'''
		Convenience method for getting the trans-word to gloss-morpheme
		bilingual alignment.
		'''
		return self.get_bilingual_alignment(self.trans.id, self.glosses.id)
	
	def get_gloss_lang_alignment(self):
		'''
		Convenience method for getting the gloss-word to lang-word
		token based alignment
		'''
		return self.gloss.get_aligned_tokens()
		
		
	#===========================================================================
	# ALIGNMENT STUFF
	#===========================================================================
		
	def get_bilingual_alignment(self, src_id, tgt_id):
		'''
		Retrieve the bilingual alignment (assuming that the source tier is
		the translation words and that the target tier is the gloss morphemes.)
		'''
		# TODO: Make the search for bilingual alignments dynamic
		ba_tier = self.find(attributes={'source':src_id, 'target':tgt_id})
		ba_tier.__class__ = RGBilingualAlignmentTier
		
		a = Alignment()
		# Now, iterate through the alignment tier
		for ba in ba_tier:
			ba.__class__ = RGBilingualAlignment
			src_item = self.find(id=ba.source)
			
			# There may be multiple targets, so get all the ids
			# and find them...
			tgt_ids = get_alignment_expression_ids(ba.target)
			for tgt in tgt_ids:
				tgt_item = self.find(id=tgt)
				a.add((src_item.index, tgt_item.index))
				
		return a
		
	def set_bilingual_alignment(self, src_tier, tgt_tier, aln, created_by = None):
		'''
		Specify the source tier and target tier, and create a bilingual alignment tier
		between the two, using the indices specified by the Alignment aln.
				
		:param src_tier: The tier that will be the source for bilingual alignments.
		:type src_tier: RGTier
		:param tgt_tier: The tier that will be the target for bilingual alignments.
		:type tgt_tier: RGTier
		:param aln: The alignment to be added
		:type aln: Alignment
		'''
		# Remove the previous alignment, if it exists.
		prev_ba_tier = self.find(attributes={'source':src_tier.id, 'target':tgt_tier.id})
		if prev_ba_tier:
			prev_ba_tier.delete()
		
		# Just to make things neater, let's sort the alignment by src index.
		aln = sorted(aln, key = lambda x: x[0])
		
		# Start by creating the alignment tier.
		ba_tier = RGBilingualAlignmentTier(id = self.askTierId('bilingual-alignments', 'a'), source = src_tier.id, target = tgt_tier.id)
		
		# Add the "created-by" attribute if one is specified.
		if created_by:
			ba_tier.attributes['created-by'] = created_by
				
		for src_i, tgt_i in aln:
			src_token = src_tier[src_i-1]
			tgt_token = tgt_tier[tgt_i-1]
			
			ba_tier.add_pair(src_token.id, tgt_token.id)
			
		self.add(ba_tier)
			
	def heur_align(self, **kwargs):
		'''
		Heuristically align the gloss and translation lines of this instance.
		'''
		
		# If given the "tokenize" option, use the tokens
		# split at the morpheme level
		
		if kwargs.get('tokenize', True):
			gloss_tokens = self.glosses.tokens()
		else:
			gloss_tokens = self.gloss.tokens()
			
		trans_tokens = self.trans.tokens()
		
		aln = heur_alignments(gloss_tokens, trans_tokens, **kwargs).flip()
		
		# Now, add these alignments as bilingual alignments...
		self.set_bilingual_alignment(self.trans, self.glosses, aln, created_by='intent-heuristic')
		
		
	
	# • POS Tag Manipulation ---------------------------------------------------------------
	
	def add_pos_tags(self, tier_id, tags):
		'''
		Assign a list of pos tags to the tier specified by tier_id. The number of tags
		must match the number of items in the tier.
		
		:param tier_id: The id for the tier
		:type tier_id: str
		:param tags: A list of POS tag strings
		:type tags: [str]
		'''
		
		# Determine the id of this new tier...
		new_id = tier_id+'-pos'
		
		# Delete that tier if it exists...
		if self.find(new_id): self.find(new_id).delete()
		
		# Find the tier that we are adding tags to.
		tier = self.find(id=tier_id)
		
		# We assume that the 
		assert len(tier) == len(tags)
		
		# Create the POS tier
		pt = RGTokenTier(type='pos', id=tier_id+'-pos', alignment=tier_id)
		self.add(pt)
		
		# Go through the words and add the tags.
		for w, tag in zip(tier.items, tags):
			p = RGToken(id=pt.askItemId(), alignment=w.id, text=tag)
			pt.add(p)			
			
	def get_pos_tags(self, tier_id):
		'''
		Retrieve the pos tags if they exist for the given tier id...
		
		:param tier_id: Id for the tier to find tags for
		:type tier_id: str
		'''
		
		pos_tier = self.find(attributes={'alignment':tier_id}, type='pos')
		
		if pos_tier is not None:
			pos_tier.__class__ = RGTokenTier
			return pos_tier
		
		
		
	def get_lang_sequence(self):
		'''
		Retrieve the language line, with as many POS tags as are available.
		'''
		# TODO: This is another function that needs reworking
		w_tags = self.get_pos_tags(self.lang.id)
		
		seq = []
		
		for w in self.lang:
			w_tag = w_tags.find(attributes={'alignment':w.id})
			if not w_tag:
				w_tag = 'UNK'
				
			w_content = w.get_content().lower()
			w_content = surrounding_quotes_and_parens(remove_hyphens(w_content))
			
			w_content = re.sub(punc_re, '', w_content)
			
			
			seq.append(POSToken(w_content, label=w_tag))
		return seq
	
	# • POS Tag Production -----------------------------------------------------
		
	def tag_trans_pos(self, tagger, **kwargs):
		'''
		Run the stanford tagger on the translation words and return the POS tags.
		
		:param tagger: The active POS tagger model.
		:type tagger: StanfordPOSTagger
		'''
		
		trans_tags = [i.label for i in tagger.tag(self.trans.text())]
		
		# Add the generated pos tags to the tier.
		self.add_pos_tags(self.trans.id, trans_tags)
		return trans_tags
			
		
	def classify_gloss_pos(self, classifier, **kwargs):
		'''
		Run the classifier on the gloss words and return the POS tags.
		
		:param classifier: the active mallet classifier to classify this language line.
		:type classifier: MalletMaxent
		'''
		
		kwargs['prev_gram'] = None
		kwargs['next_gram'] = None
		
		tags = []
		
		# Iterate over the gloss tokens...
		for i, gloss_token in enumerate(self.gloss.tokens()):

			# Manually ensure punctuation.
			if re.match('[\.\?"\';/,]+', gloss_token.seq):
				tags.append('PUNC')
			else:
				
				# lowercase the token...
				gloss_token = gloss_token.lower()
				
				#===================================================================
				# Make sure to set up the next and previous tokens for the classifier
				# if they are requested...
				#===================================================================
				if i+1 < len(self.gloss):
					kwargs['next_gram'] = self.gloss.tokens()[i+1]
				if i-1 >= 0:
					kwargs['prev_gram'] = self.gloss.tokens()[i-1]
					
				# The classifier returns a Classification object which has all the weights...
				# obtain the highest weight.
				result = classifier.classify_string(gloss_token, **kwargs)
				
				best = result.largest()
				
				# Return the POS tags
				tags.append(best[0])
			
		self.add_pos_tags(self.gloss.id, tags)
		return tags
		
	# • POS Tag Projection -----------------------------------------------------
	def project_trans_to_gloss(self):
		
		# Remove the previous tags if they are present...
		prev_t = self.find(type='pos', id='gw-pos')
		if prev_t: prev_t.delete()
		
		# Get the trans tags...
		trans_tags = self.get_pos_tags(self.trans.id)
		
		# Get the alignment...
		t_g_aln = sorted(self.get_trans_gloss_alignment())
		
		# Create the new pos tier.
		# TODO: There should be a more unified approach to transferring tags.
		pt = RGTokenTier(type='pos', id='gw-pos', alignment='gw')
		
		
		
		for t_i, g_i in t_g_aln:
			t_word = self.trans.get_index(t_i)
			t_tag = trans_tags[t_i-1]
			
			g_morph = self.glosses.get_index(g_i)
			g_morph.__class__ = RGMorph
			
			# TODO: Implement order of precedence here.
			g_word = g_morph.word
			
			pt.add(RGToken(id=pt.askItemId(), alignment = g_word.id, text = str(t_tag)))
			
		self.add(pt)
		
	def project_gloss_to_lang(self):
		# Get the gloss tags...
		gloss_tags = self.get_pos_tags(self.gloss.id)
		
		alignment = self.gloss.get_aligned_tokens()
		
		# If we don't have an alignment between language and gloss line,
		# throw an error.
		if not alignment:
			rgp(self)
			raise GlossLangAlignException()
		
		# Get the bilingual alignment from trans to 
		# Create the new pos tier...
		pt = RGTokenTier(type='pos', id='w-pos', alignment='w')
		
		for g_t in gloss_tags:
			g_w = self.find(g_t.alignment)
			l_w = self.find(g_w.alignment)
			
			pt.add(RGToken(id=pt.askItemId(), alignment = l_w.id, text=str(g_t)))
			
		self.add(pt)
		
	def project_trans_to_lang(self):
		# Get the trans tags...
		trans_tags = self.get_pos_tags(self.trans.id)
		
		t_l_aln = self.get_bilingual_alignment(self.trans.id, self.lang.id)
				
		# Create the new pos tier...
		pt = RGTokenTier(type='pos', id='w-pos', alignment='w')
		
		for t_i, l_i in t_l_aln:
			t_word = self.trans.get_index(t_i)
			t_tag = trans_tags[t_i-1]
			
			l_word = self.lang.get_index(l_i)
		
			pt.add(RGToken(id=pt.askItemId(), alignment = l_word.id, text = str(t_tag)))
		
		self.add(pt)
	
	
#===============================================================================
# Items
#===============================================================================
		
class RGItem(xigt.core.Item, FindMixin):
	'''
	Subclass of the xigt core "Item."
	'''
	
	def __init__(self, **kwargs):
		
		new_kwargs = {key : value for key, value in kwargs.items() if key != 'index'}
		
		super().__init__(**new_kwargs)
		
		self.start = kwargs.get('start')
		self.stop = kwargs.get('stop')
		self.index = kwargs.get('index')
		
	def copy(self, parent=None):
		'''
		Part of a recursive deep-copy function. Faster to implement here specifically than calling
		copy.deepcopy.
		
		:param parent:
		:type parent:
		'''
		new_item = RGItem(id=self.id, type=self.type,
							alignment=copy.copy(self.alignment),
							content=copy.copy(self.content),
							segmentation=copy.copy(self.segmentation),
							attributes=copy.deepcopy(self.attributes),
							text=copy.copy(self.text),
							tier=parent)
		return new_item
		
	
			
			

class RGLine(RGItem):
	'''
	Subtype for "lines" (raw or normalized)
	'''
	pass

class RGPhrase(RGItem):
	'''
	Subtype for phrases...
	'''
	
	def words_tier(self, words_name, words_letter):
		
		# Tokenize the words in this phrase...
		words = utils.token.tokenize_item(self)
		
		# Create a new word tier to hold the tokenized words...
		wt = RGWordTier(id = words_letter, type=words_name, segmentation=self.tier.id, igt=self.igt)
		for w in words:
			# Create a new word that is a segmentation of this tier.
			rw = RGWord(id=wt.askItemId(), segmentation='%s[%s:%s]' % (self.id, w.start, w.stop), tier=wt)
			wt.add(rw)
		
		return wt

class RGToken(RGItem):
	'''
	A subtype of item for items that can be considered tokens.
	'''
	
	def __init__(self, index=None, **kwargs):
		RGItem.__init__(self, **kwargs)
		self.index = index

class RGWord(RGToken):
	'''
	A specific type of item for handling words
	'''

class RGMorph(RGToken):
	'''
	A specific type of item for handling sub-word-level items.
	'''
	
	def __init__(self, words=[], **kwargs):
		RGItem.__init__(self, **kwargs)
		self._words = words
		
	@property
	def word(self):
		'''
		Attempt to find the word item(s) that this morph resolves to.
		'''

		if self.content:
			id = get_alignment_expression_ids(self.content)[0]
		elif self.segmentation:
			id = get_alignment_expression_ids(self.segmentation)[0]
		
		word = self.tier.igt.find(id=id)		
		word.__class__ = RGWord
		return word
			
			
		
class RGBilingualAlignment(RGItem):
	'''
	Item to hold a bilingual alignment.
	'''
	def __init__(self, source=None, target=None, **kwargs):
		super().__init__(**kwargs)
		
		if source:
			self.attributes['source'] = source
		if target:
			self.attributes['target'] = target
			
	def add_tgt(self, tgt):
		if self.attributes['target']:
			self.attributes['target'] += ','+tgt
		else:
			self.attributes['target'] = tgt
			
		
	@property	
	def source(self):
		if 'source' in self.attributes:
			return self.attributes['source']
		else:
			return None
		
	@property
	def target(self):
		if 'target' in self.attributes:
			return self.attributes['target']
		else:
			return None
			
	
	

#===============================================================================
# Tiers
#===============================================================================

class RGTier(xigt.core.Tier, RecursiveFindMixin):
	
	def copy(self, parent=None):
		'''
		Perform a deep copy.
		'''
		# TODO: make sure there's no reason content or alignment
		#       should be anything other than strings.
		new_t = RGTier(id=self.id, type=self.type,
					alignment=copy.copy(self.alignment),
					content=copy.copy(self.content),
					segmentation=copy.copy(self.segmentation),
					attributes=copy.deepcopy(self.attributes),
					metadata=copy.copy(self.metadata),
					items=None, igt=parent)
		
		for item in self.items:
			new_t.add(item.copy(parent=new_t))
			
		return new_t

	def findUUID(self, uu):
		retlist = []
		if self.attributes.get('uuid') == uu:
			retlist.append(self)
		for i in self.items:
			retlist.extend(i.findUUID(uu))
			
		return retlist
	
	def add(self, obj):
		'''
		Override the default add method to place indices on
		elements.
		'''
		obj.index = len(self)+1
		xigt.core.Tier.add(self, obj)
		
	def get_index(self, index):
		'''
		Get the item at the given index, indexed from 1
		
		:param index: index of the element (starting from 1)
		:type index: int
		'''
		return self.items[index-1]
		
	def delUUIDs(self):
		if 'uuid' in self.attributes:
			del self.attributes['uuid']
		for i in self.items:
			i.delUUIDs()
	
	def askItemId(self):
		return '%s%d' % (self.id, self.askIndex())
	
	def askIndex(self):
		return len(self.items)+1
	
	def text(self):
		'''
		Return a whitespace-delimeted string consisting of the
		elements of this tier.
		'''
		return ' '.join([str(i) for i in self.tokens()])
	
	def tokens(self):
		'''
		Return a list of the content of this tier.
		'''
		return [Token(i.get_content(), index=i.index) for i in self]

	@property
	def index(self):
		'''
		Return the integer index (from zero) of this element in its
		parent tier.
		'''
		return self.igt.tiers.index(self)
	
	def delete(self):
		'''
		Remove this tier from its parent, and refresh 
		the index to notify the instance of its removal.
		'''
		del self.igt.tiers[self.index]
		self.igt.refresh_index()
	
#===============================================================================
# Bilingual Alignment Tier
#===============================================================================
class RGBilingualAlignmentTier(RGTier):
	'''
	Special tier type for handling bilingual alignments.
	'''
	def __init__(self, source=None, target=None, **kwargs):
		super().__init__(type='bilingual-alignments', **kwargs)
		
		if source:
			self.attributes['source'] = source
		
		if target:
			self.attributes['target'] = target
	
		
			
	def add_pair(self, src, tgt):
		'''
		Add a (src,tgt) pair of ids to the tier if they are not already there,
		otherwise add the tgt on to the src. (We are operating on the paradigm
		here that the source can specify multiple target ids, but only one srcid
		per item).
		'''
		i = self.find(attributes={'source':src, 'target':tgt})
		
		# If the source is not found, add
		# a new item.
		if not i:
			 ba = RGBilingualAlignment(id=self.askItemId(), source=src, target=tgt)
			 self.add(ba)
			 
		# If the source is already here, add the target to its
		# target refs.
		else:
			i.attributes['target'] += ',' + tgt
		
	
	

class RGLineTier(RGTier):
	'''
	Tier type that contains only "lines" 
	'''

class RGPhraseTier(RGTier):
	'''
	Tier type that contains phrases.
	'''
	
class RGTokenTier(RGTier):
	'''
	Tier type that can be considered to contain tokens.
	'''
	
	def get_aligned_tokens(self):
		'''
		Function to return the alignment indices between this tier and another
		it is aligned with.
		'''
		
		a = Alignment()
		for item in self:
			ia = item.alignment
			if ia:
				aligned_w = self.igt.find(id=ia)
				a.add((item.index, aligned_w.index))
		return a
	
	def set_aligned_tokens(self, tgt_tier, aln, aln_method=None):
		'''
		Given an alignment, set the alignments correspondingly.
		
		NOTE: This function should only be used for the alignment="" attribute, which is
			  reserved for aligning items of the same supertype. (e.g. morphemes and glosses)
			  and SHOULD NOT be used for aligning, say, gloss morphs to the translation line.
		'''
		# First, set our alignment target to the provided
		# tier.
		self.alignment = tgt_tier.id
		
		# Set the alignment method if we have it specified.
		#self.attributes['']
		self.metadata = [RGMetadata(type='xigt-meta',attributes={'alignment-method':'giza'},text=[RGMeta(type='alignment-method', attributes={'alignment-method':'giza'})])]
		
		# Also, blow away any previous alignments.
		for item in self:
			del item.attributes['alignment']
				
		
		# Next, select the items from our tier (src) and tgt tier (tgt)
		# and align them.
		for src_i, tgt_i in aln:
			# Get the tokens (note that the indexing is from 1
			# when using alignments, as per GIZA standards)
			src_token = self[src_i-1]
			tgt_token = tgt_tier[tgt_i-1]
			
			src_token.alignment = tgt_token.id
			
		
	
	
class RGWordTier(RGTokenTier):
	'''
	Tier type that contains words.
	'''
	
	def morph_tier(self, type, letter):
		'''
		Given the "words" in this tier, segment them. 
		'''
		mt = RGMorphTier(id=letter, igt=self.igt, content=self.id, type=type)
		
		for word in self:
			morphs = utils.token.tokenize_item(word, utils.token.morpheme_tokenizer)
			for morph in morphs:
				rm = RGMorph(id=mt.askItemId(), content='%s[%s:%s]' % (word.id, morph.start, morph.stop), index=mt.askIndex())
				mt.add(rm)
				
				
		return mt
	
	def word_align(self, wt):
		'''
		Given another word tier, attempt to align it word by word.
		'''

		if len(self) != len(wt):
			raise GlossLangAlignException('Gloss and language lines could not be auto-aligned for igt "%s"' % self.igt.id)
		else:
			# Note on the tier the alignment
			self.alignment = wt.id
			
			# Align the words 1-to-1, left-to-right
			for my_word, their_word in zip(self, wt):
				my_word.alignment = their_word.id
				
						
		
class RGMorphTier(RGTokenTier):
	'''
	Tier type that contains morphemes.
	'''	
			
		
						
		
	
	
#===============================================================================
# Other Metadata
#===============================================================================
	
	
class RGMetadata(Metadata):
	pass

class RGMeta(Meta):
	pass

#===============================================================================
# Encode
#===============================================================================
def rgp(o):
	print(rgencode(o))

def rgencode(o):
	if isinstance(o, Tier):
		return encode_tier(o)
	elif isinstance(o, Item):
		return encode_item(o)
	elif isinstance(o, Igt):
		return encode_igt(o)
	elif isinstance(o, XigtCorpus):
		return ''.join(encode_xigtcorpus(o))
	else:
		raise Exception('%s is not a XIGT object, but is: %s' % (o, type(o)))

#===============================================================================
# Unit Tests
#===============================================================================


		
		

class TextParseTest(TestCase):
	
	def setUp(self):
		self.txt = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''
		
		self.igt = RGIgt.fromString(self.txt)
		
	
	def line_test(self):
		'''
		Test that lines are rendered correctly.
		'''
		self.assertEqual(self.igt.gloss.text(), 'I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec')
		self.assertEqual(self.igt.trans.text(), 'I made the child eat rice')
		
	def glosses_test(self):
		'''
		Test that the glosses are rendered correctly.
		'''
		self.assertEqual(self.igt.glosses.text(), 'I Nom child Dat rice Acc eat Caus Pst Dec')
		
	def word_align_test(self):
		'''
		Test that the gloss has been automatically aligned at the word level correctly.
		'''
		at = self.igt.gloss.get_aligned_tokens()
		
		self.assertEqual(at, Alignment([(1,1),(2,2),(3,3),(4,4)]))
		
	def set_align_test(self):
		'''
		Check setting alignment attributes between tiers.
		'''
		self.igt.gloss.set_aligned_tokens(self.igt.lang, Alignment([(1,1),(2,2)]))
		self.assertEqual(self.igt.gloss.get_aligned_tokens(), Alignment([(1,1),(2,2)]))
		
	def set_bilingual_align_test(self):
		'''
		Set the bilingual alignment manually, and ensure that it is read back correctly.
		'''
		
		a = Alignment([(1,1),(1,2),(2,8),(4,3),(5,7),(6,5)])
		self.igt.set_bilingual_alignment(self.igt.trans, self.igt.glosses, a)
		
		self.assertEqual(a, self.igt.get_trans_gloss_alignment())
		
class XigtParseTest(TestCase):
	'''
	Testcase to make sure we can load from XIGT objects.
	'''
	def setUp(self):
		self.xc = RGCorpus.load(c['xigt_ex'])
		
	def xigt_load_test(self):
		pass
	
	def giza_align_test(self):
		self.xc.giza_align_t_g()
		giza_aln = self.xc[0].get_trans_gloss_alignment()
		
		giza_a = Alignment([(3, 2), (2, 8), (5, 7), (4, 3), (1, 1), (6, 5)])
		
		self.assertEquals(giza_a, giza_aln)
		
	def heur_align_test(self):
		self.xc.heur_align()
		aln = self.xc[0].get_trans_gloss_alignment()
		a = Alignment([(5, 7), (6, 5), (1, 1), (4, 3)])
		self.assertEquals(a, aln)
		
class CopyTest(TestCase):
		def setUp(self):
			self.txt = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''
			self.igt = RGIgt.fromString(self.txt)
			self.corpus = RGCorpus(igts=[self.igt])
			
		def test_copy(self):
			
			new_c = self.corpus.copy()
			
			self.assertNotEqual(id(self.corpus), id(new_c))
			
			# Assert that there is no alignment.
			self.assertIsNone(self.corpus.find(type='bilingual-alignments'))
			
			new_c.heur_align()
			self.assertIsNotNone(new_c.find(type='bilingual-alignments'))
			self.assertIsNone(self.corpus.find(id='bilingual-alignments'))

class POSTestCase(TestCase):
	
	def setUp(self):
		self.txt = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''
		self.igt = RGIgt.fromString(self.txt)
		self.tags = ['PRON', 'NOUN', 'NOUN', 'VERB']
	
	def test_add_pos_tags(self):
		
		self.igt.add_pos_tags('gw', self.tags)
		
		self.assertEquals(self.igt.get_pos_tags('gw').tokens(), self.tags)
		
	def test_classify_pos_tags(self):
		pos_dict = pickle.load(open(c['pos_dict'], 'rb'))
		tags = self.igt.classify_gloss_pos(MalletMaxent(c['classifier_model']), posdict=pos_dict)
		
		self.assertEqual(tags, self.tags)
		
		
	def test_tag_trans_line(self):
		tagger = StanfordPOSTagger(c['stanford_tagger_trans'])
		self.igt.tag_trans_pos(tagger)
		
from igt.rgxigtutils import create_words_tier, create_phrase_tier, morph_align
