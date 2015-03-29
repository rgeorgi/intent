'''
Subclassing of the xigt package to add a few convenience methods.


'''

#===============================================================================
# Logging
#===============================================================================

import logging, pickle, re, copy


from intent.interfaces.stanford_tagger import StanfordPOSTagger
import sys
import string



# Set up logging ---------------------------------------------------------------
PARSELOG = logging.getLogger(__name__)

# XIGT imports -----------------------------------------------------------------
import xigt.core
from xigt.core import Metadata, Meta, Tier, Item, Igt,\
	get_alignment_expression_ids, XigtCorpus, ALIGNMENT, SEGMENTATION, CONTENT
from xigt.codecs import xigtxml
from xigt.codecs.xigtxml import encode_tier, encode_item, encode_igt, encode_xigtcorpus

# INTERNAL imports -------------------------------------------------------------
from .igtutils import merge_lines, clean_lang_string, clean_gloss_string,\
	clean_trans_string, remove_hyphens, surrounding_quotes_and_parens, punc_re
import intent.utils.token
from intent.utils.env import c, tagger_model, posdict, classifier
from intent.alignment.Alignment import Alignment, heur_alignments
from intent.utils.token import Token, POSToken
from intent.interfaces.giza import GizaAligner

# Other imports ----------------------------------------------------------------
from unittest.case import TestCase
from uuid import uuid4
from collections import defaultdict



#===============================================================================
# String Conventions ---
#===============================================================================

# Lines ------------------------------------------------------------------------
ODIN_TYPE  = 'odin'

STATE_ATTRIBUTE = 'state'

RAW_STATE, RAW_ID     = 'raw', 'r'
CLEAN_STATE, CLEAN_ID = 'clean', 'c'
NORM_STATE, NORM_ID   = 'normalized', 'n'

# Words ------------------------------------------------------------------------

WORDS_TYPE = 'words'

TRANS_WORD_TYPE = 'words'
GLOSS_WORD_TYPE = 'words'
LANG_WORD_TYPE  = 'words'

LANG_WORD_ID = 'w'
GLOSS_WORD_ID = 'gw'
TRANS_WORD_ID = 'tw'

# Phrases ----------------------------------------------------------------------

TRANS_PHRASE_TYPE = 'translations'
LANG_PHRASE_TYPE  = 'phrases'

TRANS_PHRASE_ID = 't'
LANG_PHRASE_ID = 'p'

# Morphemes --------------------------------------------------------------------

LANG_MORPH_TYPE = 'morphemes'
GLOSS_MORPH_TYPE = 'glosses'

LANG_MORPH_ID = 'm'
GLOSS_MORPH_ID= 'g'

# POS --------------------------------------------------------------------------
POS_TIER_TYPE = 'pos'

LANG_POS_ID  = 'w-pos'
GLOSS_POS_ID = 'g-pos'
TRANS_POS_ID = 'tw-pos'

# Alignments -------------------------------------------------------------------

ALN_TIER_TYPE = 'bilingual-alignments'

L_T_ALN_ID = 'a'
G_T_ALN_ID = 'a'

SOURCE_ATTRIBUTE = 'source'
TARGET_ATTRIBUTE = 'target'

# Phrase structures ------------------------------------------------------------

PS_TIER_TYPE = 'phrase-structure'

GEN_PS_ID   = 'ps'
LANG_PS_ID  = 'ps'
GLOSS_PS_ID = 'ps'
TRANS_PS_ID = 'ps'

PS_CHILD_ATTRIBUTE = 'children'

# Dependencies -----------------------------------------------------------------

DS_TIER_TYPE = 'dependencies'

GEN_DS_ID   = 'ds'
LANG_DS_ID  = 'ds'
GLOSS_DS_ID = 'ds'
TRANS_DS_ID = 'ds'

DS_DEP_ATTRIBUTE = 'dep'
DS_HEAD_ATTRIBUTE = 'head'

#===============================================================================
# Exceptions
#===============================================================================

class RGXigtException(Exception): pass

class NoODINRawException(RGXigtException):	pass 

class TextParseException(RGXigtException):	pass

class NoLangLineException(TextParseException):	pass

class NoGlossLineException(TextParseException):	pass

class NoTransLineException(TextParseException):	pass

class GlossLangAlignException(RGXigtException):	pass

class ProjectionException(RGXigtException): pass

class ProjectionTransGlossException(ProjectionException): pass

class PhraseStructureProjectionException(RGXigtException): pass


def project_creator_except(msg_start, msg_end, created_by):
	
	if created_by:
		msg_start += ' by the creator "%s".' % created_by
	else:
		msg_start += '.'
	raise ProjectionException(msg_start + ' ' + msg_end)

#===============================================================================
# Mixins
#===============================================================================

class FindMixin():
	'''
	Extension of the recursive search for non-iterable elements.
	'''
	
	def find_self(self, id=None, id_base=None, attributes=None, type = None, segments = None, contents=None):
		'''
		Check on this element to see if it matches the find criteria. Must satisfy all the specified
		criteria, (they are considered unspecified if "None")
		
		:param id:
		:type id: str
		:param id_base:
		:type id_base: str
		:param attributes:
		:type attributes: dict
		:param type:
		:type type: str
		:param segments:
		:type segments: str
		'''
		
		id_match = id is None or (self.id == id)
		id_base_match = id_base is None or (re.search('^(\w+)', self.id).group(1) == id_base)
		type_match = type is None or (self.type == type)
		attr_match = attributes is None or (set(attributes.items()).issubset(set(self.attributes.items())))
		seg_match  = segments is None or (hasattr(self, SEGMENTATION) and segments in get_alignment_expression_ids(self.segmentation))
		
		# TODO: not sure the contents is working...
		cnt_match = contents is None or (hasattr(self, CONTENT) and contents in get_alignment_expression_ids(self.content))
		
		# At least ONE thing must be specified
		assert any([id, id_base, attributes, type, segments, contents])
		
		if id_match and id_base_match and type_match and attr_match and seg_match and cnt_match:
			return self
		else:
			return None
		
	def find(self, id=None, id_base = None, attributes=None, type=None, segments=None, contents=None):
		return self.find_self(id, id_base, attributes, type, segments, contents)
	
	def findall(self, id=None, id_base=None, attributes=None, type=None, segments=None, contents=None):
		found = self.find_self(id, id_base, attributes, type, segments, contents)
		if found:
			return [found]
		else:
			return []

class RecursiveFindMixin(FindMixin):

	def find(self, id=None, id_base=None, attributes=None, type=None, segments=None, contents=None):
		'''
		Generic find function for non-iterable elements. NOTE: This version stops on the first match.
		
		:param id: id of an element to find, or None to search by attribute.
		:type id: str
		:param attributes: key:value pairs that are an inclusive subset of those found in the desired item.
		:type attributes: dict
		'''
		if self.find_self(id,id_base, attributes,type,segments,contents) is not None:
			return self
		else:
			found = None
			for child in self:
				found = child.find(id, id_base, attributes, type, segments, contents)
				if found is not None:
					break
			return found
		
	def findall(self, id=None, id_base = None, attributes=None, type=None, segments=None, contents=None):
		'''
		Find function that does not terminate on the first match.
		'''
		if self.find_self(id, id_base, attributes, type, segments, contents) is not None:
			return [self]
		else:
			found = []
			for child in self:
				new_found = child.findall(id, id_base, attributes, type, segments, contents)
				found.extend(new_found)
			return found
				

#===============================================================================
# • Parse Tree Functions ---
#===============================================================================
def read_pt(tier):
	
	# Assume that we are reading from a phrase structure tier.
	assert tier.type == PS_TIER_TYPE
	
	# Provide a way to look up the nodes by their ID so we can
	# pair them directly later...
	node_dict = {}
	
	# Also, keep track of the child-parent relationships that need
	# to be constructed.
	children_dict = defaultdict(list)
	
	for node in tier:
	
		# 1) If the node has an alignment, that means it's a terminal ----------
		aln = node.attributes.get(ALIGNMENT)
		if aln:
			w = tier.igt.find(id=aln)
			idx = w.index
			w = w.get_content()			
			n = IdTree(node.get_content(), [w], index=idx)
			
			# If this is a preterminal, it shouldn't have children.
			assert not node.attributes.get(PS_CHILD_ATTRIBUTE)
			
			
		else:
			n = IdTree(node.get_content(), [])
		
			# 2) If there is a "children" attribute, split it on whitespace and store ---
			#    those IDs to revisit, with the current node as the parent.
			childids = node.attributes.get(PS_CHILD_ATTRIBUTE, '').split()
			
			for childid in childids:
				children_dict[node.id].append(childid)
		
		
		node_dict[node.id] = n
		
			
	# 3) Revisit the children and make the linkages.
	for parent_id in children_dict.keys():
		parent_n = node_dict[parent_id]
		for child_id in children_dict[parent_id]:
			child_n = node_dict[child_id]
			parent_n.append(child_n)
		
		
	# Finally, pick an arbitrary node, and try to find the root.
	assert child_n, "There should have been at least one child found..."
	
	
	
	return child_n.root()
	

def gen_id(id_str, num, letter=False):
	'''
	Unified method to generate an ID string. Ex: `gen_id('i',2)` returns `i2` if letter is False or `ib` if True.
	
	:param id_str: Basis to generate the ID.
	:type id_str: str
	:param num: Number to append
	:param letter: 
	:type letter:
	'''
	if not letter:
		return '{}{}'.format(id_str, num+1)
	else:					
		assert num < 26, "Too many tiers of the same type"
		letters = string.ascii_lowercase
		return '{}-{}'.format(id_str, letters[num])


#===============================================================================

class RGCorpus(xigt.core.XigtCorpus, RecursiveFindMixin):

	def askIgtId(self):
		return gen_id('i', len(self.igts), letter=False)
	
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
		
		# Make sure that there are no spaces within a token, this will get us
		# all out of alignment...
		
		g_sents = []
		t_sents = []
		
		for inst in self:
			g_sent = []
			t_sent = []
			
			for gloss in inst.glosses.tokens():
				g_sent.append(re.sub('\s+','', gloss.get_content().lower()))
			g_sents.append(' '.join(g_sent))
			
			for trans in inst.trans.tokens():
				t_sent.append(re.sub('\s+', '', trans.get_content().lower()))
			t_sents.append(' '.join(t_sent))
			
		
		
		
		if resume:
			# Next, load up the saved gloss-trans giza alignment model
			ga = GizaAligner.load(c['g_t_prefix'], c['g_path'], c['t_path'])
	
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
		
		ga = GizaAligner()
		
		l_t_asents = ga.temp_train(l_sents, t_sents)
		
		assert len(l_t_asents) == len(self)
		
		for l_t_asent, igt in zip(l_t_asents, self):
			t_l_aln = l_t_asent.aln.flip()
			igt.set_bilingual_alignment(igt.trans, igt.lang, t_l_aln, created_by = 'intent-giza')
		
		
			
	def heur_align(self, error=False):
		'''
		Perform heuristic alignment between the gloss and translation.
		'''
		for igt in self:
			try:
				g_heur_aln = igt.heur_align()
			except NoTransLineException as ntle:
				logging.warn(ntle)
				if error:
					raise ntle
		
		
		
	
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
		rt = RGLineTier(id = RAW_ID, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE}, igt=inst)
		
		for lineno, linetag, linetxt in lines:
			l = RGLine(id = rt.askItemId(), text=linetxt, attributes={'tag':linetag, 'line':lineno}, tier=rt)
			rt.add(l)
			
		inst.add(rt)
		
		# --- 4) Do the enriching if necessary

		inst.basic_processing(require_1_to_1 = require_1_to_1)
		# TODO: Clean up this exception handling
		try:
			inst.enrich_instance()
		except TextParseException as ngle:
			PARSELOG.warning(ngle)
		
		
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
		
		:param type: Tier type to count
		:type type: str
		:param id: ID to assign the instance, followed by a number
		:type id: str
		'''
		
		tiers = self.findall(type=type)
		numtiers = len(tiers)
		
		return gen_id(id, numtiers, letter=True)

			
	# • Basic Tier Creation ------------------------------------------------------------
	
	def raw_tier(self):
		'''
		Retrieve the raw ODIN tier, otherwise raise an exception.
		'''
		raw_tier = self.find(type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE})
		
		if not raw_tier:
			raise NoODINRawException('No raw tier found.')
		else:
			return raw_tier
	
	def clean_tier(self):
		'''
		If the clean odin tier exists, return it. Otherwise, create it.
		'''
		
		# If a clean tier already exists, return it.
		clean_tier = self.find(type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:CLEAN_STATE})
		if clean_tier:
			return clean_tier
		
		else:
			# Otherwise, we will make our own:
			raw_tier = self.raw_tier()
			
			# Now, create the normalized and clean tiers...
			clean_tier = RGLineTier(id = CLEAN_ID, type=ODIN_TYPE,
									 attributes={STATE_ATTRIBUTE:CLEAN_STATE,
												ALIGNMENT:raw_tier.id})

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

		# Remember, we want to match "L" for a tag L+LN, but NOT LN+M
		raw_lines = [i for i in raw_tier if tag in i.attributes['tag'].split('+')]
		
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
			normal_tier = self.find(type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:NORM_STATE})
			if normal_tier:
				return normal_tier
			else:
				raw_tier = self.raw_tier()
				clean_tier = self.clean_tier()
				
				normal_tier = RGLineTier(id = NORM_ID, type=ODIN_TYPE,
										 attributes={STATE_ATTRIBUTE:NORM_STATE, ALIGNMENT:clean_tier.id})
				
				self.add_normal_line(normal_tier, 'L', clean_lang_string, merge)
				self.add_normal_line(normal_tier, 'G', clean_gloss_string, merge)
				self.add_normal_line(normal_tier, 'T', clean_trans_string, merge)
				
				self.add(normal_tier)
				return normal_tier
			
			
	def create_phrases_words(self, orig_tag, word_type, word_id, phrase_type, phrase_id):
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
		words_tier = self.find(type=word_type, id_base=word_id)
		if words_tier:
			words_tier.__class__ = RGWordTier
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
				if not phrase_type:
					words_tier =  create_words_tier(line, word_id, word_type)
					self.add(words_tier)
					return words_tier
				
				# Otherwise, find or create the phrase tier, and base the 
				# words tier off of that.
				else:

					# -- 1) If the phrase tier already exists, get it.
					phrase_tier = self.find(type = phrase_type, id_base = phrase_id)
					if phrase_tier:
						phrase_tier.__class__ = RGPhraseTier
		
					
					# -- 4) If such a phrase tier does not exist, create it.
					else:
						phrase_tier = create_phrase_tier(line, phrase_id, phrase_type)
						self.add(phrase_tier)
					
					# Finally, create a words tier based on the phrase tier.
					words_tier = create_words_tier(phrase_tier[0], word_id, word_type)
					self.add(words_tier)
					
					# And finally, return our words tier.
					
					return words_tier
				
						
	

	@property
	def lang(self):
		lt = self.create_phrases_words('L', LANG_WORD_TYPE, LANG_WORD_ID, LANG_PHRASE_TYPE, LANG_PHRASE_ID)
		if not lt:
			raise NoLangLineException('No lang line available for igt "%s"' % self.id)
		else:
			return lt
		
	@property
	def gloss(self):
		gt = self.create_phrases_words('G', GLOSS_WORD_TYPE, GLOSS_WORD_ID, None, None)
		if not gt:
			raise NoGlossLineException('No gloss line available for igt "%s"' % self.id)
		else:
			return gt
		

	# • Properties -------------------------------------------------------------

		
	@property
	def glosses(self):
		glosses = self.find(type=GLOSS_MORPH_TYPE)
		if glosses:
			glosses.__class__ = RGMorphTier
			return glosses
		else:
			gt = self.gloss.morph_tier(GLOSS_MORPH_TYPE, GLOSS_MORPH_ID)
			self.add(gt)
			return gt
	
	@property
	def morphemes(self):
		morphemes = self.find(type=LANG_MORPH_TYPE)
		if morphemes:
			morphemes.__class__ = RGMorphTier
			return morphemes
		else:
			mt = self.lang.morph_tier(LANG_MORPH_TYPE, LANG_MORPH_ID)
			self.add(mt)
			return mt
		

	@property
	def trans(self):
		tt = self.create_phrases_words('T', TRANS_WORD_TYPE, TRANS_WORD_ID, TRANS_PHRASE_TYPE, TRANS_PHRASE_ID)		
		if not tt:
			raise NoTransLineException('No trans line available for igt "%s"' % self.id)
		else:
			return tt
		
	# • Alignment --------------------------------------------------------------

	def get_trans_gloss_alignment(self, created_by=None):
		'''
		Get the alignment between trans words and gloss words. 
		'''
		# If we already have this alignment, just return it.
		trans_gloss = self.get_bilingual_alignment(self.trans.id, self.gloss.id, created_by)
		if trans_gloss:
			return trans_gloss
		
		# Otherwise, let's create it from the glosses alignment
		else:
			trans_glosses = self.get_bilingual_alignment(self.trans.id, self.glosses.id, created_by)
			
			if not trans_glosses:
				raise ProjectionTransGlossException("Trans-to-gloss alignment must already exist, otherwise create with giza or heur")
			
			new_trans_gloss = Alignment()
			
			for trans_i, gloss_i in trans_glosses:
				gloss_m = self.glosses[gloss_i-1]
				gloss_w = word(gloss_m)
				new_trans_gloss.add((trans_i, gloss_w.index))
				
			return new_trans_gloss

	def get_trans_glosses_alignment(self, created_by=None):
		'''
		Convenience method for getting the trans-word to gloss-morpheme
		bilingual alignment.
		'''
		return self.get_bilingual_alignment(self.trans.id, self.glosses.id, created_by=None)
	
	
	def get_gloss_lang_alignment(self):
		'''
		Convenience method for getting the gloss-word to lang-word
		token based alignment
		'''
		return self.gloss.get_aligned_tokens()
	
	def get_trans_gloss_lang_alignment(self):
		'''
		Get the translation to lang alignment, travelling through the gloss line.
		'''
		
		tg_aln = self.get_trans_gloss_alignment()
		gl_aln = self.get_gloss_lang_alignment()

		# Combine the two alignments...		
		a = Alignment()
		for t_i, g_i in tg_aln:
			l_js = [l_j for (g_j, l_j) in gl_aln if g_j == g_i]
			for l_j in l_js:
				a.add((t_i, l_j))
		return a
			
				
		
		
	#===========================================================================
	# ALIGNMENT STUFF
	#===========================================================================
		
	def get_bilingual_alignment(self, src_id, tgt_id, created_by=None):
		'''
		Retrieve the bilingual alignment (assuming that the source tier is
		the translation words and that the target tier is the gloss morphemes.)
		'''
		
		attributes = {SOURCE_ATTRIBUTE:src_id, TARGET_ATTRIBUTE:tgt_id}
		# If we have the created_by trait, look for that, too.
		if created_by:
			attributes['created-by'] = created_by
			
		ba_tier = self.find(attributes=attributes)
		if not ba_tier:
			return None
		else:
			ba_tier.__class__ = RGBilingualAlignmentTier
			
			a = Alignment()
			# Now, iterate through the alignment tier
			for ba in ba_tier:
				ba.__class__ = RGBilingualAlignment
				src_item = self.find(id=ba.source)
				
				if not src_item:
					PARSELOG.warn('Instance had src ID "%s", but no such ID was found.' % src_item)
				else:
					# There may be multiple targets, so get all the ids
					# and find them...
					tgt_ids = get_alignment_expression_ids(ba.target)
					for tgt in tgt_ids:
						tgt_item = self.find(id=tgt)
						
						if tgt_item:
							a.add((src_item.index, tgt_item.index))
						else:
							PARSELOG.warn('Instance had target ID "%s", but no such ID was found.' % tgt_item)
					
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
		
		# Look for a previously created alignment of the same type.
		attributes = {SOURCE_ATTRIBUTE:src_tier.id, TARGET_ATTRIBUTE:tgt_tier.id}
		if created_by:
			attributes['created-by'] = created_by
			

		# If it already exists, delete it and overwrite.		
		prev_ba_tier = self.find(attributes=attributes)
		if prev_ba_tier:
			prev_ba_tier.delete()
		
		# Just to make things neater, let's sort the alignment by src index.
		aln = sorted(aln, key = lambda x: x[0])
		
		# Start by creating the alignment tier.
		ba_tier = RGBilingualAlignmentTier(id = self.askTierId(ALN_TIER_TYPE, G_T_ALN_ID), source = src_tier.id, target = tgt_tier.id)
		
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
	
	def add_pos_tags(self, tier_id, tags, created_by = None):
		'''
		Assign a list of pos tags to the tier specified by tier_id. The number of tags
		must match the number of items in the tier.
		
		:param tier_id: The id for the tier
		:type tier_id: str
		:param tags: A list of POS tag strings
		:type tags: [str]
		'''
		
		# See if we have a pos tier that's already been assigned by this method.
		attributes = {} if not created_by else {'created-by':created_by}
		prev_tier = self.find(type=POS_TIER_TYPE, attributes=attributes)
		
		# And delete it if so.
		if prev_tier: prev_tier.delete()
		
	
		# Determine the id of this new tier...
		new_id = self.askTierId(POS_TIER_TYPE, tier_id+'-pos') 
		
		# Find the tier that we are adding tags to.
		tier = self.find(id=tier_id)
		
		# We assume that the length of the tags we are to add is the same as the
		# number of tokens on the target tier.
		assert len(tier) == len(tags)
		
		# Create the POS tier
		pt = RGTokenTier(type=POS_TIER_TYPE, id=new_id, alignment=tier_id, attributes=attributes)
		self.add(pt)
		
		# Go through the words and add the tags.
		for w, tag in zip(tier.items, tags):
			p = RGToken(id=pt.askItemId(), alignment=w.id, text=tag)
			pt.add(p)			
			
	def get_pos_tags(self, tier_id, created_by = None):
		'''
		Retrieve the pos tags if they exist for the given tier id...
		
		:param tier_id: Id for the tier to find tags for
		:type tier_id: str
		'''
		
		attributes = {ALIGNMENT:tier_id}
		
		# Also add the created-by feature to select which we are looking for.
		if created_by:
			attributes['created-by'] = created_by
			
		pos_tier = self.find(attributes=attributes, type=POS_TIER_TYPE)
		
		
		if pos_tier is not None:
			pos_tier.__class__ = RGTokenTier
			return pos_tier
		
		
		
	def get_lang_sequence(self, created_by = None, unk_handling=None):
		'''
		Retrieve the language line, with as many POS tags as are available.
		'''
		# TODO: This is another function that needs reworking
		w_tags = self.get_pos_tags(self.lang.id, created_by)
		
		if not w_tags:
			project_creator_except("Language-line POS tags were not found", "To obtain the language line sequence, please project or annotate the language line.", created_by)
		
		seq = []
		
		for w in self.lang:
			w_tag = w_tags.find(attributes={ALIGNMENT:w.id})
			if not w_tag:
				if unk_handling == None:
					w_tag = 'UNK'
				elif unk_handling == 'noun':
					w_tag = 'NOUN'
				else:
					raise ProjectionException('Unknown unk_handling attribute')
				
			w_content = w.get_content().lower()
			w_content = surrounding_quotes_and_parens(remove_hyphens(w_content))
			
			w_content = re.sub(punc_re, '', w_content)
			
			
			seq.append(POSToken(w_content, label=w_tag))
		return seq
	
	# • POS Tag Production -----------------------------------------------------
		
	def tag_trans_pos(self, tagger):
		'''
		Run the stanford tagger on the translation words and return the POS tags.
		
		:param tagger: The active POS tagger model.
		:type tagger: StanfordPOSTagger
		'''
		
		trans_tags = [i.label for i in tagger.tag(self.trans.text())]
		
		# Add the generated pos tags to the tier.
		self.add_pos_tags(self.trans.id, trans_tags, created_by = 'intent-tagger')
		return trans_tags
			
		
	def classify_gloss_pos(self, classifier, **kwargs):
		'''
		Run the classifier on the gloss words and return the POS tags.
		
		:param classifier: the active mallet classifier to classify this language line.
		:type classifier: MalletMaxent
		'''
		
		attributes = {ALIGNMENT:self.gloss.id}
		# Put our created_by attribute in here...
		created_by = kwargs.get('created_by', 'intent-classify')
		if created_by:
			attributes['created-by'] = created_by		
		
		 
		# Search for a previous run and Remove if found...
		prev_tier = self.find(type='pos', attributes=attributes)
		if prev_tier:
			prev_tier.delete()
		
		kwargs['prev_gram'] = None
		kwargs['next_gram'] = None
		
		tags = []
		
		# Iterate over the gloss tokens...
		for i, gloss_token in enumerate(self.gloss.tokens()):

			# Manually ensure punctuation.
			if re.match('[\.\?"\';/,]+', gloss_token.seq):
				tags.append('PUNC')
			else:
				
				# TODO: Yet another whitespace issue..
				# TODO: Also, somewhat inelegant forcing it to a string like this...
				gloss_token = re.sub('\s+', '', str(gloss_token))
				
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
			
		self.add_pos_tags(self.gloss.id, tags, created_by)
		return tags
		
	# • POS Tag Projection -----------------------------------------------------
	def project_trans_to_gloss(self, created_by=None, pos_creator = None):
		'''
		Project POS tags from the translation words to the gloss words.
		'''
		
		# Remove previous gloss tags created by us if specified...
		attributes = {ALIGNMENT:self.gloss.id}
		# Set the created-by attribute if specified.
		if created_by:
			attributes['created-by'] = created_by
		
		# Remove the previous tags if they are present...
		prev_t = self.find(type=POS_TIER_TYPE, attributes=attributes)
		if prev_t: prev_t.delete()
		
		# Get the trans tags...
		trans_tags = self.get_pos_tags(self.trans.id, created_by = pos_creator)
		
		# If we don't get any trans tags back, throw an exception:
		if not trans_tags:
			project_creator_except("There were no translation-line POS tags found", 
								"Please create the appropriate translation-line POS tags before projecting.", 
								pos_creator)
		
		# Get the alignment between the trans words and the gloss words.
		t_g_aln = sorted(self.get_trans_gloss_alignment(created_by))
		
		# Create the new pos tier.
		# TODO: There should be a more unified approach to transferring tags.
		
		pt = RGTokenTier(type=POS_TIER_TYPE, id=self.askTierId(POS_TIER_TYPE, GLOSS_POS_ID), alignment=self.gloss.id, attributes=attributes)
		
		for t_i, g_i in t_g_aln:
			g_word = self.gloss.get_index(g_i)
			t_tag = trans_tags[t_i-1]
			
			# TODO: Implement order of precedence here.
			
			pt.add(RGToken(id=pt.askItemId(), alignment = g_word.id, text = str(t_tag)))
			
		self.add(pt)
		
	def project_gloss_to_lang(self, created_by = None, pos_creator = None, unk_handling=None, classifier=None, posdict=None):
		'''
		Project POS tags from gloss words to language words. This assumes that we have
		alignment tags on the gloss words already that align them to the language words.
		'''
		# Get the gloss tags...
		
		attributes = {} if not pos_creator else {'created-by':created_by}
		
		gloss_tags = self.get_pos_tags(self.gloss.id, created_by=pos_creator)
		
		# If we don't have gloss tags by that creator...
		if not gloss_tags:
			project_creator_except("There were no gloss-line POS tags found",
									"Please create the appropriate gloss-line POS tags before projecting.",
									pos_creator)
		
		alignment = self.gloss.get_aligned_tokens()
		
		# If we don't have an alignment between language and gloss line,
		# throw an error.
		if not alignment:
			raise GlossLangAlignException()
		

		
		# Get the bilingual alignment from trans to 
		# Create the new pos tier...
		pt = RGTokenTier(type=POS_TIER_TYPE, id=self.askTierId(POS_TIER_TYPE, LANG_POS_ID),
							alignment=self.lang.id, attributes=attributes)
		

		
		for g_idx, l_idx in alignment:
			l_w = self.lang.get_index(l_idx)
			g_w = self.gloss.get_index(g_idx)
			
			# Find the tag associated with this word.
			g_tag = gloss_tags.find(attributes={ALIGNMENT:g_w.id})
			
			# If no gloss tag exists for this...
			if not g_tag:
				label = 'UNK'
				
				# If we are not handling unknowns, we could
				# assign it "UNK", OR we could just skip it
				# and leave it unspecified.
				# Here, we choose to skip.
				if unk_handling is None:
					continue
				
				# If we are doing the "Noun" method, then we
				# replace all the unknowns with "NOUN"
				elif unk_handling == 'noun':
					label = 'NOUN'
					
				# Finally, we can choose to run the classifier on
				# the unknown gloss words.
				elif unk_handling == 'classify':
					kwargs = {'posdict':posdict}    # <-- Initialize the new kwargs for the classifier.
					if not classifier:
						raise ProjectionException('To project with a classifier, one must be provided.')
					
					# Set up for the classifier...
					kwargs['prev_gram'] = ''
					kwargs['next_gram'] = ''
					
					if g_idx > 1:
						kwargs['prev_gram'] = self.gloss.get_index(g_idx-1).get_content()
					if g_idx < len(self.gloss):
						kwargs['next_gram'] = self.gloss.get_index(g_idx+1).get_content()
					
					# Replace the whitespace in the gloss word for error
					# TODO: Another whitespace replacement handling.
					g_content = re.sub('\s+','', g_w.get_content())
					
					
					label = classifier.classify_string(g_content, **kwargs).largest()[0]
				
				else:
					raise ProjectionException('Unknown unk_handling method "%s"' % unk_handling)
			
			else:
				label = str(g_tag)
				
			pt.add(RGToken(id=pt.askItemId(), alignment = l_w.id, text=label))
		
		self.add(pt)
		

		
	def project_trans_to_lang(self, created_by=None, pos_creator=None, aln_creator=None):
		'''
		Project POS tags from the translation line directly to the language
		line. This assumes that we have a bilingual alignment between
		translation words and language words already.
		
		:param created_by: The attribute that the projected tags will have
		:param pos_creator: The pos tags from which to select for projection
		'''
		
		attributes = {} if not created_by else {'created-by':created_by}
		
		# Get the trans tags...
		trans_tags = self.get_pos_tags(self.trans.id, created_by=pos_creator)
		
		t_l_aln = self.get_bilingual_alignment(self.trans.id, self.lang.id, created_by=aln_creator)
		if not t_l_aln:
			raise ProjectionException("No trans-lang alignment found...")
		
				
		# Create the new pos tier...
		pt = RGTokenTier(type=POS_TIER_TYPE, id=LANG_POS_ID, alignment=self.lang.id, attributes=attributes)
		
		for t_i, l_i in t_l_aln:
			t_word = self.trans.get_index(t_i)
			t_tag = trans_tags[t_i-1]
			
			l_word = self.lang.get_index(l_i)
		
			pt.add(RGToken(id=pt.askItemId(), alignment = l_word.id, text = str(t_tag)))
		
		self.add(pt)
	
	# • Translation Line Parsing -----------------------------------------------
	def parse_translation_line(self, parser, pt=False, dt=False):
		'''
		Parse the translation line in order to project phrase structure.
		
		:param parser: Initialized StanfordParser
		:type parser: StanfordParser
		'''
		assert pt or dt, "At least one of pt or dt should be true."
		
		result = parser.parse(self.trans.text())
		
		if pt:
			self.create_pt_tier(result.pt, self.trans)
		if dt:
			self.create_dt_tier(result.dt)

		
	def create_pt_tier(self, pt, w_tier):
		'''
		Given a phrase tree, create a phrase tree tier. The :class:`intent.trees.IdTree` passed in must
		have the same number of leaves as words in the translation line.
		
		:param pt: Phrase tree.
		:type pt: :class:`intent.trees.IdTree`
		:param w_tier: Word tier
		:type pt: RGWordTier
		'''
		
		# 1) Start by creating a phrase structure tier -------------------------
		pt_tier = RGPhraseStructureTier(type=PS_TIER_TYPE, id=self.askTierId(PS_TIER_TYPE, GEN_PS_ID), alignment=w_tier.id)

		pt.assign_ids(pt_tier.id)
		
		# We should get back the same number of tokens as we put in
		assert len(pt.leaves()) == len(w_tier)
		
		leaves = list(pt.leaves())
		preterms = list(pt.preterminals())
		
		assert len(leaves) == len(preterms)
		
		# 2) Now, run through the leaves and the preterminals ------------------
		for wi, preterm in zip(w_tier, preterms):
			
			# Note that the preterminals align with a given word...
			pi = RGItem(id=preterm.id, alignment=wi.id, text=preterm.label())
			pt_tier.add(pi)
			
		# 3) Finally, run through the rest of the subtrees. --------------------
		for st in pt.nonterminals():
			child_refs = ' '.join([s.id for s in st])
			si = RGItem(id=st.id, attributes={PS_CHILD_ATTRIBUTE:child_refs}, text=st.label())
			pt_tier.add(si)
			
		
		
		# 4) And add the created tier to this instance. ------------------------
		self.add(pt_tier)
		
	def get_trans_parse_tier(self):
		'''
		Get the phrase structure tier aligned with the translation words.
		'''
		return self.find(type=PS_TIER_TYPE, attributes={ALIGNMENT:self.trans.id})
		
	def project_pt(self):
		
		trans_parse_tier = self.get_trans_parse_tier()
		
		if trans_parse_tier is None:
			raise PhraseStructureProjectionException('Translation tier not found for instance "%s"' % self.id)
		
		trans_tree = read_pt(trans_parse_tier)
		
		# This might raise a ProjectionTransGlossException if the trans and gloss
		# alignments don't exist.
		tl_aln = self.get_trans_gloss_lang_alignment()
		
		pt = project_ps(trans_tree, self.lang, tl_aln)
		

		self.create_pt_tier(pt, self.lang)
		
			
		
		
		
	def create_dt_tier(self, dt):
		'''
		Create the dependency structure tier based on the ds that is passed in. The :class:`intent.trees.DepTree` 
		structure that is passed in must be based on the words in the translation line, as the indices from the
		dependency tree will be used to identify the tokens.
		
		:param dt: Dependency tree to create a tier for. 
		:type dt: DepTree
		'''
		
		# 1) Start by creating dt tier -----------------------------------------
		dt_tier = RGTier(type=DS_TIER_TYPE, id=self.askTierId(DS_TIER_TYPE, GEN_DS_ID),
						attributes = {DS_DEP_ATTRIBUTE:self.trans.id, DS_HEAD_ATTRIBUTE:self.trans.id})
		
		# 2) Next, simply iterate through the tree and make the head/dep mappings. 
		for head_i, dep_i in dt.index_pairs():
			
			attributes={DS_DEP_ATTRIBUTE:self.trans.get_index(dep_i).id}
			
			if head_i != 0:
				attributes[DS_HEAD_ATTRIBUTE] = self.trans.get_index(head_i).id
							
				
			di = RGItem(id=dt_tier.askItemId(), attributes=attributes)
			dt_tier.add(di)
		
		self.add(dt_tier)
		
	
		
	
		
		
	
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
		words = intent.utils.token.tokenize_item(self)
		
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
			self.attributes[SOURCE_ATTRIBUTE] = source
		if target:
			self.attributes[TARGET_ATTRIBUTE] = target
			
	def add_tgt(self, tgt):
		if self.attributes[TARGET_ATTRIBUTE]:
			self.attributes[TARGET_ATTRIBUTE] += ','+tgt
		else:
			self.attributes[TARGET_ATTRIBUTE] = tgt
			
		
	@property	
	def source(self):
		if 'source' in self.attributes:
			return self.attributes[SOURCE_ATTRIBUTE]
		else:
			return None
		
	@property
	def target(self):
		if 'target' in self.attributes:
			return self.attributes[TARGET_ATTRIBUTE]
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
		
	
	def askItemId(self):
		return gen_id(self.id, len(self), letter=False)
	
	def askIndex(self):
		return len(self.items)+1
	
	def text(self, remove_whitespace_inside_tokens = True):
		'''
		Return a whitespace-delimeted string consisting of the
		elements of this tier. Default to removing whitespace
		that occurs within a token.
		'''
		tokens = [str(i) for i in self.tokens()]
		if remove_whitespace_inside_tokens:
			
			# TODO: Another whitespace replacement handling
			tokens = [re.sub('\s+','',i) for i in tokens]
			
		return ' '.join(tokens)
	
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
		super().__init__(type=ALN_TIER_TYPE, **kwargs)
		
		if source:
			self.attributes[SOURCE_ATTRIBUTE] = source
		
		if target:
			self.attributes[TARGET_ATTRIBUTE] = target
	
		
			
	def add_pair(self, src, tgt):
		'''
		Add a (src,tgt) pair of ids to the tier if they are not already there,
		otherwise add the tgt on to the src. (We are operating on the paradigm
		here that the source can specify multiple target ids, but only one srcid
		per item).
		'''
		i = self.find(attributes={SOURCE_ATTRIBUTE:src, TARGET_ATTRIBUTE:tgt})
		
		# If the source is not found, add
		# a new item.
		if not i:
			 ba = RGBilingualAlignment(id=self.askItemId(), source=src, target=tgt)
			 self.add(ba)
			 
		# If the source is already here, add the target to its
		# target refs.
		else:
			i.attributes[TARGET_ATTRIBUTE] += ',' + tgt
		
	
	

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
			del item.attributes[ALIGNMENT]
				
		
		# Next, select the items from our tier (src) and tgt tier (tgt)
		# and align them.
		for src_i, tgt_i in aln:
			# Get the tokens (note that the indexing is from 1
			# when using alignments, as per GIZA standards)
			src_token = self[src_i-1]
			tgt_token = tgt_tier[tgt_i-1]
			
			src_token.alignment = tgt_token.id
			
		
class RGPhraseStructureTier(RGTier):
	'''
	Specialized tier that will hold a phrase structure tree, or read it if it doesn't exist.
	'''
	def __init__(self, pt=None, **kwargs):
		RGTier.__init__(self, **kwargs)
		self._tree = pt
		
	@property
	def tree(self):
		'''
		If the tier already has a IdTree, simply return it. Otherwise, create it by reading the Xigt.
		'''
		if self._tree is None:
			self._tree = read_pt(self.igt)
			
		return self._tree
			
	
class RGWordTier(RGTokenTier):
	'''
	Tier type that contains words.
	'''
	
	@classmethod
	def from_string(cls, string, **kwargs):
		wt = cls(**kwargs)
		for w in intent.utils.token.tokenize_string(string):
			wi = RGToken(id=wt.askItemId(), text=str(w))
			wt.add(wi)
		return wt
	

	
	def morph_tier(self, type, id):
		'''
		Given the "words" in this tier, segment them. 
		'''
		mt = RGMorphTier(id=id, content=self.id, type=type)
		
		for word in self:
			
			morphs = intent.utils.token.tokenize_item(word, intent.utils.token.morpheme_tokenizer)
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
	
	
class RGMetadata(Metadata): pass

class RGMeta(Meta): pass

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
		
		self.assertEqual(a, self.igt.get_trans_glosses_alignment())
		
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
		giza_aln = self.xc[0].get_trans_glosses_alignment()
		
		giza_a = Alignment([(3, 2), (2, 8), (5, 7), (4, 3), (1, 1), (6, 5)])
		
		self.assertEquals(giza_a, giza_aln)
		
	def heur_align_test(self):
		self.xc.heur_align()
		aln = self.xc[0].get_trans_glosses_alignment()
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
		pos_dict = pickle.load(open(posdict, 'rb'))
		tags = self.igt.classify_gloss_pos(MalletMaxent(classifier), posdict=pos_dict)
		
		self.assertEqual(tags, self.tags)
		
		
	def test_tag_trans_line(self):
		tagger = StanfordPOSTagger(tagger_model)
		self.igt.tag_trans_pos(tagger)
		
from .rgxigtutils import create_words_tier, create_phrase_tier, morph_align,\
	word
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.trees import IdTree, project_ps