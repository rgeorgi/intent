'''
Subclassing of the xigt package to add a few convenience methods.


'''
import xigt.core
from xigt.core import Metadata, Meta, Tier, Item, Igt,\
	get_alignment_expression_ids, XigtCorpus
import sys
import re
from xigt.codecs import xigtxml
from unittest.case import TestCase
from uuid import uuid4
from xigt.codecs.xigtxml import encode_tier, encode_item, encode_igt
from igt.igtutils import merge_lines, clean_lang_string, clean_gloss_string,\
	clean_trans_string

import utils.token
from collections import defaultdict
import interfaces.giza
from utils.setup_env import c
from xigt.codecs.xigttxt import encode_xigtcorpus


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

class RGCorpus(xigt.core.XigtCorpus):
	def delUUIDs(self):
		for i in self.igts:
			i.delUUIDs()
			
	def askIgtId(self):
		return 'i%d' % (len(self.igts)+1)
	
	def __len__(self):
		return len(self._list)
	
	@classmethod
	def load(cls, path):
		xc = xigtxml.load(path)
		xc.__class__ = RGCorpus
		
		# Now, convert all the IGT instances to RGIgt instances.
		for igt in xc.igts:
			igt.__class__ = RGIgt			
			
			for tier in igt.tiers:
				tier.__class__ = RGTier
				
			igt.enrich_instance()
			
		return xc
	
	def giza_align(self):
		'''
		Perform giza alignments on the gloss and translation
		lines.
		'''
		
		g_sents = [i.glosses.text().lower() for i in self]
		t_sents = [i.trans.text().lower() for i in self]
		
		ga = interfaces.giza.GizaAligner.load(c['g_t_prefix'], c['g_path'], c['t_path'])
		
		print(ga.force_align(g_sents, t_sents)[0].aln)
		
		
		
		
	
#===============================================================================
# IGT Class
#===============================================================================

class RGIgt(xigt.core.Igt):

	@classmethod
	def fromXigt(cls, o, **kwargs):
		'''
		Subclass a XIGT object into the child class.
		
		@param cls: The subclass constructor.
		@param o: The original XIGT object.
		'''
						
		return cls(id=o.id, type=o.type, attributes=o.attributes, metadata=o.metadata, tiers=o.tiers, corpus=o.corpus)

	def getTier(self, type):
		return [t for t in self.tiers if t.type == type] 
		
	def findUUID(self, uu):
		retlist = []	
		for t in self.tiers:
			retlist.extend(t.findUUID(uu))
		
		if not retlist:
			return None
		else:
			return retlist[0]
	
	def askTierId(self, type):
		'''
		Generate a new tierID, based on the number of tiers that already exist for that type.
		'''
		numtiers = len(self.getTier(type))
		return '%s%d' % (type, numtiers+1)
	
	def delUUIDs(self):
		if 'uuid' in self.attributes:
			del self.attributes['uuid']
		for t in self.tiers:
			t.delUUIDs()
			
	
	def raw_tier(self):
		'''
		Retrieve the raw ODIN tier, otherwise raise an exception.
		'''
		raw_tier = [t for t in self if t.type == 'odin' and t.attributes['state'] == 'raw']
		if not raw_tier:
			raise NoODINRawException('No raw tier found.')
		else:
			return raw_tier[0]
	
	def clean_tier(self, merge=True):
		'''
		If the clean odin tier exists, return it. Otherwise, create it.
		'''
		
		# If a clean tier already exists, return it.
		clean_tier = [t for t in self.tiers if t.type == 'odin' and t.attributes['state'] == 'normalized']
		if clean_tier:
			return clean_tier[0]
		
		else:
			# Otherwise, we will make our own:
			raw_tier = self.raw_tier()
			
			raw_l_s = [i for i in raw_tier if 'L' in i.attributes['tag']]
			raw_g_s = [i for i in raw_tier if 'G' in i.attributes['tag']]
			raw_t_s = [i for i in raw_tier if 'T' in i.attributes['tag']]
			
			# Execute errors if a given line is not found...
			if not raw_t_s:
				raise NoTransLineException('No translation line found in instance "%s"' % self.id)
			if not raw_g_s:
				raise NoGlossLineException('No gloss line found in instance "%s"' % self.id)
			if not raw_l_s:
				raise NoLangLineException('No language line found in instance "%s"' % self.id)
			
			# Now, create the normalized tier...
			normal_tier = RGLineTier(id = 'n', type='odin',
									 attributes={'state':'normalized', 'alignment':raw_tier.id})
			
			# Initialize the new lines...
			l_norm = RGLine(id='n1', alignment=raw_l_s[0].id, tier=normal_tier, attributes={'tag':'L'})
			g_norm = RGLine(id='n2', alignment=raw_g_s[0].id, tier=normal_tier, attributes={'tag':'G'})
			t_norm = RGLine(id='n3', alignment=raw_t_s[0].id, tier=normal_tier, attributes={'tag':'T'})
			
			# Either merge the lines to create single lines, or just take
			# the first...
				
			if merge:
				l_cont = merge_lines([l.get_content() for l in raw_l_s])
				g_cont = merge_lines([g.get_content() for g in raw_g_s])
				t_cont = merge_lines([t.get_content() for t in raw_t_s])
				
				# Make sure the alignment is updated if we do merge lines.
				l_norm.alignment = ','.join([l.id for l in raw_l_s])
				g_norm.alignment = ','.join([g.id for g in raw_g_s])
				t_norm.alignment = ','.join([t.id for t in raw_t_s])
	
			else:
				l_cont = raw_l_s[0]
				g_cont = raw_g_s[0]
				t_cont = raw_t_s[0]
				
			# Now clean the various strings....
			l_cont = clean_lang_string(l_cont)
			g_cont = clean_gloss_string(g_cont)
			t_cont = clean_trans_string(t_cont)
				
			# Set the item's text to the cleaned result....
			l_norm.text = l_cont
			g_norm.text = g_cont
			t_norm.text = t_cont
			
			# Add the normalized lines to the tier...
			normal_tier.add_list([l_norm, g_norm, t_norm])			
	
			# Now, add the normalized tier to ourselves...				
			self.add(normal_tier)
			return normal_tier
			
	@classmethod
	def fromString(cls, string):
		'''
		Method to parse and create an IGT instance from odin-style text.
		'''
		# Start by looking for the doc_id, and the line range.
		doc_re = re.search('doc_id=([0-9]+)\s([0-9]+)\s([0-9]+)\s(.*)\n', string)
		docid, lnstart, lnstop, tagtypes = doc_re.groups()
		
		
		inst = cls(id = str(uuid4()), attributes={'doc-id':docid, 
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
		inst.enrich_instance()
		
		return inst
		
	def enrich_instance(self):
		# Create the clean tier
		self.clean_tier()
		
		# Create the word and phrase tiers...
		self.trans
		self.gloss
		self.lang
		
		# Create the morpheme tiers...
		self.glosses
		self.morphemes
		
		# And do word-to-word alignment if it's not already done.
		if not self.gloss.alignment:
			self.gloss.word_align(self.lang) 
			
		# Finally, do morpheme-to-morpheme alignment between gloss
		# and language if it's not already done...
		if not self.glosses.alignment:
			self.glosses.gloss_align(self.morphemes)
		
	@property
	def glosses(self):
		glosses = [t for t in self if t.type == 'glosses']
		if glosses:
			glosses[0].__class__ = RGMorphTier
			return glosses[0]
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
	def gloss(self):
		return self.obtain_phrase_and_words_tiers('G', 'gloss-phrases', 'g', 'gloss-words', 'gw')
	
	@property
	def trans(self):
		return self.obtain_phrase_and_words_tiers('T', 'translations', 't', 'translation-words', 'tw')
		
	@property
	def lang(self):
		return self.obtain_phrase_and_words_tiers('L', 'phrases', 'p', 'words', 'w')	
			
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
		c = self.clean_tier()
		
		# -- 1) Retrieve the original line from the clean tier.
		line = [l for l in c if orig_tag in l.attributes['tag']][0]
				
		# -- 2) If the phrase tier already exists, get it.
		phrase_tier = [tier for tier in self if tier.type == phrase_name]
		if phrase_tier:
			phrase_tier = phrase_tier[0]
			phrase_tier.__class__ = RGPhraseTier
			
		# -- 4) If such a phrase tier does not exist, create it.
		else:
			phrase_tier = RGPhraseTier(id=phrase_letter, type=phrase_name, attributes={'content':c.id}, igt=self)
			phrase_item = RGPhrase(id='%s1' % phrase_letter, content=line.id, tier=phrase_tier)
			phrase_tier.add(phrase_item)
			self.add(phrase_tier)
			
							
		# -- 5) Finally, get the words tier if it exists.
		words_tier = [tier for tier in self if tier.type == words_name]
		if words_tier:
			wt = words_tier[0]
			wt.__class__ = RGWordTier
			return words_tier[0]
		
		# -- 6) ...otherwise, create it.
		else:
			words_tier = phrase_tier[0].words_tier(words_name, words_letter)
				
			# -- 6) Add the created translation-word tier to the instance
			self.add(words_tier)
			
			# -- 7) Finally, return the translation word tier.
			return words_tier
		
	def findId(self, id):
		'''
		Recursively search for a given ID through the tier and its items. 
		'''
		if self.id == id:
			return self
		else:
			found = None
			for tier in self:
				found = tier.findId(id)
				if found:
					break
			return found

#===============================================================================
# Items
#===============================================================================
		
class RGItem(xigt.core.Item):
	'''
	Subclass of the xigt core "Item."
	'''
	
	def __init__(self, id=None, type=None,
				alignment=None, segmentation=None,
				attributes=None,
				content=None, text=None, tier=None, **kwargs):
		xigt.core.Item.__init__(self, id, type, alignment, content, segmentation, attributes, text, tier)
		
		self.start = kwargs.get('start')
		self.stop = kwargs.get('stop')
		self.index = kwargs.get('index')
		
	@classmethod
	def fromItem(cls, i, start=None, stop=None, index=-1):
		
		if i.segmentation:
			start, stop = [int(s) for s in re.search('\[([0-9]+):([0-9]+)\]', i.segmentation).groups()]
			
		
		return cls(id=i.id, type=i.type, alignment=i.alignment, content=i.content,
					segmentation=i.segmentation, attributes=i.attributes, text=i.text,
					tier=i.tier, index=int(i.attributes.get('index', index)), start=start, stop=stop)
	
	def findUUID(self, uu):
		retlist = []
		if self.attributes.get('uuid') == uu:
			retlist.append(self)
		return retlist
	
	def delUUIDs(self):
		if 'uuid' in self.attributes:
			del self.attributes['uuid']
			
	def findId(self, id):
		if self.id == id:
			return self
		else:
			return None
			

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

		word = self.tier.igt.findId(id)
		word.__class__ = RGWord
		return word
			
			
		
		
	

#===============================================================================
# Tiers
#===============================================================================

class RGTier(xigt.core.Tier):
	
	@classmethod
	def fromTier(cls, t):
		
		items = [RGItem.fromItem(i) for i in t.items]
		
		return cls(id=t.id, type=t.type, alignment=t.alignment, content=t.content,
					segmentation=t.segmentation, attributes=t.attributes, metadata=t.metadata,
					items=items, igt=t.igt)

	def findUUID(self, uu):
		retlist = []
		if self.attributes.get('uuid') == uu:
			retlist.append(self)
		for i in self.items:
			retlist.extend(i.findUUID(uu))
			
		return retlist
	
	def findAttr(self, key, value):
		found = None
		
		for item in self:
			if item.attributes[key] == value:
				found = item
				break
			
		return found
	
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
		return ' '.join(self.tokens())
	
	def tokens(self):
		'''
		Return a list of the content of this tier.
		'''
		return [i.get_content() for i in self]
	
	def findId(self, id):
		'''
		Recursively search for a given ID in this tier and its
		items. 
		'''
		if self.id == id:
			return self
		else:
			found = None
			for item in self:
				item.__class__ = RGItem
				found = item.findId(id)
				if found:
					break
			return found
	

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
				
			self.igt.refresh_index()
						
		
class RGMorphTier(RGTokenTier):
	'''
	Tier type that contains morphemes.
	'''	
	def gloss_align(self, mt):
		'''
		Align glosses with the morpheme tier.
		@param mt:
		'''

		

		# Let's count up how many morphemes there are
		# for each word on the translation line...
		lang_word_dict = defaultdict(list)
		for m in mt:
			m.__class__ = RGMorph
			
			# Add this morpheme to the dictionary, so we can keep
			# count of how many morphemes align to a given word.
			lang_word_dict[m.word.id].append(m)
			
			
		# Now, iterate over our morphs.
		for m in self:
			m.__class__ = RGMorph
			
			# Find our parent word, and it's
			# alignment.
			w = m.word
			other_w_id = w.alignment
			
			# Next, let's see what unaligned morphs there are
			other_w_list = lang_word_dict[other_w_id]
			
			# If there's only one morph left, align with that.
			if len(other_w_list) == 1:
				m.alignment = other_w_list[0].id
				
			# If there's more, pop one off the beginning of the list and use that.
			elif len(other_w_list) > 1:
				other_m = other_w_list.pop(0)
				m.alignment = other_m.id
			
		
						
		
	
	
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
def rgencode(o):
	if isinstance(o, Tier):
		return encode_tier(o)
	elif isinstance(o, Item):
		return encode_item(o)
	elif isinstance(o, Igt):
		return encode_igt(o)
	elif isinstance(o, XigtCorpus):
		return encode_xigtcorpus(o)

#===============================================================================
# Unit Tests
#===============================================================================

class TextParseTest(TestCase):
	
	def runTest(self):
		
		i = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''
		
		igt = RGIgt.fromString(i)
		self.assertEqual(igt.gloss.text(), 'I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec')
		print(rgencode(igt))