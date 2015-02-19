'''
Created on Mar 7, 2014

@author: rgeorgi
'''
from alignment.Alignment import Alignment, AlignedSent
import re
import sys

import unittest
from utils.token import Token, TokenException, Morph, tokenize_string,\
	morpheme_tokenizer, GoldTagPOSToken, whitespace_tokenizer, POSToken,\
	Tokenization
from igt.igtutils import merge_lines, clean_lang_string, clean_gloss_string,\
	clean_trans_string
import uuid
from corpora.POSCorpus import POSCorpus, POSCorpusInstance
import igt.rgxigt as rgx

from utils.setup_env import c
from alignment.morphalign import Sentence
from interfaces.giza import GizaAligner



class IGTException(Exception):
	pass

class IGTParseException(IGTException):
	pass

class IGTParseExceptionLang(IGTParseException):
	pass

class IGTParseExceptionGloss(IGTParseException):
	pass

class IGTParseExceptionTrans(IGTParseException):
	pass
	
class IGTGlossLangLengthException(IGTParseException):
	pass
		
class IGTAlignmentException(IGTException):
	pass

class IGTProjectionException(IGTException):
	pass

class IGTCorpus(rgx.RGCorpus):
	'''
	Object that will hold a corpus of IGT instances.
	'''

	def __init__(self, **kwargs):
		rgx.RGCorpus.__init__(self, id=kwargs.get('id'), attributes=kwargs.get('attributes'),
								igts=kwargs.get('igts'))
		

	def gloss_alignments(self):
		return [inst.gloss_alignments() for inst in self]

	def lang_alignments(self):
		return [inst.lang_to_trans_sent() for inst in self]
	
	def classifier_pos_corpus(self, classifier, **kwargs):
		pc = POSCorpus()
		for inst in self:
			try:
				sent = inst.lang_line_classifications(classifier, **kwargs)
				if len(sent):
					pc.add(POSCorpusInstance(sent))
			except:
				continue
		return pc
	
	
	def gloss_heuristic_alignments(self, **kwargs):
		return [inst.gloss_heuristic_alignment(**kwargs) for inst in self]
	
	@classmethod
	def from_text(cls, textfile, **kwargs):
		'''
		Read in a standard-format ODIN document of textfiles and create a corpus from it.
		'''
		# Create a new corpus
		corpus = cls()
		
		# Open the textfile, and read the contents.
		f = open(textfile, 'r', encoding='utf-8')
		data = f.read()
		f.close()
		
		# Find all the text lines
		inst_txts = re.findall('doc_id=[\s\S]+?\n\n', data)
		for inst_txt in inst_txts:
			try:
				i = IGTInstance.from_string(inst_txt, **kwargs)
				corpus.add(i)
			except IGTParseException as e:
				sys.stderr.write(str(e))
				continue
			
		return corpus
	
	
	def giza_align_g_t(self):
		'''
		Produce alignments between gloss and translation lines using giza, and the 
		saved model defined in env.conf.
		'''
		ga = GizaAligner.load(c['g_t_prefix'], c['g_path'], c['t_path'])
		
		g_sents = []
		t_sents = []
		
		for igt in self:
			i = IGTInstance.fromXigt(igt)
			
			# Initialize the whole-word sentence...
			g_s = Sentence.fromTier(i.gloss)
			t_s = Sentence.fromTier(i.trans)
			
			# Now, get the morphs from the sentence...
			g_m = g_s.morphs()
			t_m = t_s.morphs()
			
			# Now, add this to a list...
			g_sents.append(g_m.text().lower())
			t_sents.append(t_m.text().lower())
		
		# Run giza to align the sentences...
		a_sents = ga.force_align(g_sents, t_sents)	
		
		# Now, assign the alignments
		for igt, a_sent in zip(self.igts, a_sents):
			print(igt)
			
		
	
#===============================================================================
# IGT Instance Class
#===============================================================================
		
class IGTInstance(rgx.RGIgt):
	'''
	Container class for an IGT instance and all the dealings that will go on inside it.
	'''
	
		
	#===========================================================================
	# Convert Instance to XIGT
	#===========================================================================
	
	def __init__(self, id=None, type=None, attributes=None, corpus=None, tiers=None, metadata=None):
		# Start with the basics..
		rgx.RGIgt.__init__(self, id=id, type=type,
						attributes=attributes,
						tiers=tiers, metadata=metadata,
						corpus=corpus)
		
		# Either use a provided id or generated one
		self.id = id or str(uuid.uuid4())
		
		
	
		

	# GlossAlign ---------------------------------------------------------------

	@property
	def glossalign(self):
		if not hasattr(self, '_ga'):
			self._ga = self.gloss_heuristic_alignment().aln
			#ga = GizaAligner.load(c['g_path'], c['t_path'], c['g_t_prefix'])
			#self._ga = self.giza_alignment(ga).aln
		return self._ga
	
	@glossalign.setter
	def glossalign(self, v):
		self._ga = v
	
	# LangAlign ----------------------------------------------------------------
	
	@property
	def langalign(self):
		if not hasattr(self, '_la'):
			self._la = self.glossalign
		return self._la
	
	@langalign.setter
	def langalign(self, v):
		self._la = v
	
	
	#===========================================================================

	
	@classmethod
	def from_lines(cls, l, g, t, **kwargs):
		
		instid = kwargs.get('id', None)
		inst = cls(id = instid)
		
		#=======================================================================
		# Start by creating the raw odin 
		#=======================================================================
		
		raw_tier = LinesTier(type='odin', attributes={'state':'raw'}, id='r')
		
		i = 0
		
		for l_txt in l:
			raw_tier.add_line(l_txt, 'L')
			
		for g_txt in g:
			raw_tier.add_line(g_txt, 'G')

		for t_txt in t:
			raw_tier.add_line(t_txt, 'T')
			
		# Add the raw tier.
		inst.add(raw_tier)
		
		# Now, we can produce the cleaned tier.
		inst.clean
		return inst
	
	@classmethod
	def from_string(cls, string, **kwargs):
		'''
		Method to parse and create an IGT instance from text.
		
		@param cls:
		@param string:
		'''
		# Start by looking for the doc_id
		txtid = re.search('doc_id=([0-9\s]+)', string).group(1)
		inst = cls(id = txtid)
		
		# Now, find all the lines
		lines = re.findall('line=([0-9]+)\stag=(\S+):(.*)\n', string)
		
		# Merge all the lang lines into one
		l = [line[2] for line in lines if 'L' in line[1]]				
		g = [line[2] for line in lines if 'G' in line[1]]
		t = [line[2] for line in lines if 'T' in line[1]]
		
		return cls.from_lines(l,g,t,**kwargs)
		
		
	def lang_line_projections(self, tagger, **kwargs):
		
		
		# Throw an exception if we don't have a translation line to project from.
		if not self.trans:
			raise IGTProjectionException('IGT %s does not contain a translation line to project from.' % str(self))
	
		# Also, throw an exception if we don't have 1-to-1	
		if len(self.gloss) != len(self.lang):
			raise IGTGlossLangLengthException('The length of the gloss line and language line are not equal. Alignment not guaranteed.')
	
		
		# Get the language line to translation line alignment...
		aln = self.langalign
		
		# Initialize a new POS Corpus instance to hold the projected tags...
		result_tokens = POSCorpusInstance()
		
		trans_tags = tagger.tag(self.trans_texts())
		
		
		for lang_token in self.lang:
			tgt_indices = aln.src_to_tgt(lang_token.index)
			
			# Don't forget to subtract the one, since the "index" attribute
			# is counting by one...
			
			# If we have supplied a dictionary, look that up first...
			dict_tags = []
			if kwargs.get('posdict'):
				pd = kwargs.get('posdict')
				
				# Get the aligned translation words...
				trans_words = [self.trans[i-1].get_content() for i in tgt_indices]
				
				# And see which of them are in the dictionary...			
				dict_tags = [pd[w].most_frequent()[0] for w in trans_words if pd[w]]
				
				
			
			
			# Get the projected tags....
			lang_tags = [trans_tags[i-1].label for i in tgt_indices]
			
			label = None
			if dict_tags:
				label = dict_tags[0]
			elif lang_tags:
				label = lang_tags[0]
			
			if not label:
				if kwargs.get('error_on_nonproject'):				
					raise IGTProjectionException('Projection for word "%s" not possible' % lang_token.get_content())
				else:
					label = 'X'
						
			pt = POSToken(lang_token.get_content(), label=label)
			result_tokens.append(pt)
			
		return result_tokens
			
		
		# Initialize a POS tagger to tag the translation line...
		
		
		
	def lang_line_classifications(self, classifier, **kwargs):
		
		token_sequence = []
		
		# If the length of the gloss and language lines
		# does not match, skip it.
				
		if len(self.gloss) != len(self.lang):
			raise IGTGlossLangLengthException('The length of the gloss line and language line are not equal. Alignment not guaranteed.')
		
		kwargs['prev_gram'] = None
		kwargs['next_gram'] = None
		
		for i, gloss_token in enumerate(self.gloss):
			
			gloss_token = gloss_token.lower()
			
			# -- 0) Before we even get started, go ahead and assign the tag 
			#       as PUNC if it clearly is.
			if i >= len(self.lang):
				continue
					
					
					
			lang_token = self.lang[i]
			
			#===================================================================
			# Make sure to set up the next and previous tokens for the classifier
			# if they are requested...
			#===================================================================
			if i+1 < len(self.gloss):
				kwargs['next_gram'] = self.gloss[i+1]
			if i-1 >= 0:
				kwargs['prev_gram'] = self.gloss[i-1]
			
			print(lang_token.get_content())
			if re.match('^[\.,\?\-!/\(\)\*\+\:\'\"\`\{\}\]\[]+$', lang_token.get_content()):
				pos = 'PUNC'
			else:
			
				# -- 1) Start by creating a token that holds no gold label and the 
				#       content form the gold tag.
				gloss_token = GoldTagPOSToken.fromToken(gloss_token, goldlabel='NONE')
				result = classifier.classify_token(gloss_token, **kwargs)
				
				best = result.largest()
				pos = best[0]
		
			#===================================================================
			# Assign the classified gloss tokens to the language tokens.
			#===================================================================
			lt_content = lang_token.get_content()
			
			if kwargs.get('lowercase'):
				lt_content = lt_content.lower()
			
			c_token = POSToken(lt_content, label=pos, index=i+1)
			token_sequence.append(c_token)
			
			#===================================================================
			
		# Add the pos tags to the xigt representation if we haven't already.
		self.add_pos_tags(self.lang, token_sequence)
			
		return token_sequence
	
	def add_pos_tags(self, tier, pos_tags):
		
		# Start by creating a POS tier and blowing the old one away if it exists.
		pos_tier = rgx.RGTier(id=('%s-pos' % tier.id),
							alignment=tier.id, type='pos')
		
		i = 0
		for lw, pt in zip(tier, pos_tags):
			pos_item = rgx.RGItem(id=('%s%d' % (pos_tier.id, i)), 
								alignment=lw.id,
								text=pt.label)			
			i += 1
			pos_tier.add(pos_item)
			
		self.add(pos_tier)
							
			
	def text(self):
		return '%s\n%s\n%s' % (self.lang_texts(), self.gloss_texts(), self.trans_texts())
			
		
	def gloss_alignments(self):
		print(self.id)
		a = AlignedSent(self.gloss, self.trans, self.glossalign)
		a.attrs = self.attrs
		return a
	
	
	def lang_to_trans_align(self, **kwargs):
		'''
		Given the alignment of lang to gloss and
		gloss to trans, return the alignment of
		lang to trans.
		'''
		new_align = []
				
		# For each lang_index, gloss_index in the 
		# lang alignment, find what tran_indexes
		# the gloss index is aligned to, and 
		# pair those with the lang_index.
		for l_i, g_i in self.langalign:
			t_is = self.glossalign.src_to_tgt(g_i)
			for t_i in t_is:
				# Remember, a zero index means "NULL"
				if t_i > 0:
					new_align.append((l_i, t_i))
				
		# Now return our new alignment.
		return Alignment(new_align)
	
	def lang_to_trans_sent(self):
		'''
		Return the aligned sentence pair of language line to translation line
		'''
		a = AlignedSent(self.lang, self.trans, self.langalign)
		return a
	
	def append(self, item):
		rgx.RGIgt.add(self, item)	
	#def append(self, item):
	#	if not isinstance(item, IGTTier):
	#		raise IGTException('Attempt to append a non-IGTTier instance to an IGTInstance')
	#	list.append(self, item)
	
	#===========================================================================
	# Create the odin-clean tier if it does not exist.
	#===========================================================================
	
	@property
	def clean(self, merge=True):
		'''
		If the "odin-clean" tier exists, return it. Otherwise, create it.
		'''
		
		# The clean tier we are looking for must be of "odin" type, with a "normalized" state attribute
		clean_tier = [tier for tier in self if tier.type == 'odin' and tier.attributes['state'] == 'normalized']
		
		# If such a tier exists, return it. Otherwise, create it.
		if clean_tier:
			return clean_tier[0]
		
		else:
			# First, look for the raw tier.
			raw_tier = [tier for tier in self if tier.type == 'odin' and tier.attributes['state'] == 'raw']
			
			# Raise an exception if no raw tier was available.
			if not raw_tier:
				raise rgx.NoODINRawException('No raw tier found.')
			else:
				raw_tier = raw_tier[0]
			
			# Otherwise, clean up the raw tier...

			raw_l_s = [i for i in raw_tier if 'L' in i.attributes['tag']]
			raw_g_s = [i for i in raw_tier if 'G' in i.attributes['tag']]
			raw_t_s = [i for i in raw_tier if 'T' in i.attributes['tag']]
			
			# Execute errors if a given line is not found...
			if not raw_t_s:
				raise IGTParseExceptionTrans('No translation line found!')
			if not raw_g_s:
				raise IGTParseExceptionGloss('No gloss line found!')
			if not raw_l_s:
				raise IGTParseExceptionLang('No language line found!')
			
			# Create the tier that will hold the normalized bits.
			normal_tier = rgx.RGTier(id='n', igt=raw_tier.igt, type='odin', attributes={'state':'normalized', 'alignment':raw_tier.id})
			
			# Initialize the new items...
			l_norm = rgx.RGItem(id='n1', alignment=raw_l_s[0].id, tier=normal_tier, attributes={'tag':'L'})
			g_norm = rgx.RGItem(id='n2', alignment=raw_g_s[0].id, tier=normal_tier, attributes={'tag':'G'})
			t_norm = rgx.RGItem(id='n3', alignment=raw_t_s[0].id, tier=normal_tier, attributes={'tag':'T'})
			
			
			
			# Either merge the lines to create single lines, or just take
			# the first...
			
			if merge:
				l_cont = merge_lines([l.get_content() for l in raw_l_s])
				g_cont = merge_lines([g.get_content() for g in raw_g_s])
				t_cont = merge_lines([t.get_content() for t in raw_t_s])

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
			
	
	#  -----------------------------------------------------------------------------
	
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

		
		# -- 1) Retrieve the normalized tier, and create it if it does not exist.
		c = self.clean
		
		# -- 2) Retrieve the original line from the clean tier.
		line = [l for l in c if orig_tag in l.attributes['tag']][0]
				
		# -- 3) If the phrase tier already exists, get it.
		phrase_tier = [tier for tier in self if tier.type == phrase_name]
		if phrase_tier:
			phrase_tier = rgx.RGTier.fromTier(phrase_tier[0])
			
		# -- 4) If such a phrase tier does not exist, create it.
		else:
			phrase_tier = rgx.RGTier(id=phrase_letter, type=phrase_name, attributes={'content':c.id})
			phrase_item = rgx.RGItem(id='%s0' % phrase_letter, type='phrase', content=line.id)
			phrase_tier.add(phrase_item)
			self.add(phrase_tier)
							
		# -- 5) Finally, get the words tier if it exists. Otherwise, create it.
		words_tier = [tier for tier in self if tier.type == words_name]
		if words_tier:
			return WordsTier.fromTier(words_tier[0])
		else:
			words_tier = WordsTier(id=words_letter, type=words_name, attributes={'segmentation':phrase_tier.id})
			
			# Just grab the first phrase off the phrases tier. This will usually be the only
			# one, or the automated one we created.
			p1 = phrase_tier[0]
			
			# Tokenize the line, and create the items...
			for t in tokenize_string(p1.get_content()):
				word_item = rgx.RGItem(id = '%s%d' % (words_letter, t.index), type='word', text=t.content, tier=words_tier.id)				
				word_item.attributes = {'segmentation':'%s[%d:%d]' % (phrase_tier.id, t.start, t.stop),
										'index':str(t.index)}
				word_item.start = t.start
				word_item.stop = t.stop
				word_item.index = t.index
				words_tier.add(word_item)
				
			# -- 6) Add the created translation-word tier to the instance
			self.add(words_tier)
			
			# -- 7) Finally, return the translation word tier.
			return words_tier
		
	
	@property
	def gloss(self):
		return self.obtain_phrase_and_words_tiers('G', 'glosses', 'g', 'gloss-words', 'gw')
	
	@property
	def trans(self):
		return self.obtain_phrase_and_words_tiers('T', 'translations', 't', 'translation-words', 'tw')
		
	@property
	def lang(self):
		return self.obtain_phrase_and_words_tiers('L', 'phrases', 'p', 'words', 'w')

		
	def lang_texts(self, **kwargs):
		return self.lang.text(**kwargs)
		
	def gloss_texts(self, **kwargs):
		return self.gloss.text(**kwargs)	
	
	def trans_texts(self, **kwargs):
		return self.trans.text(**kwargs)
	
	def set_attr(self, key, val):
		self.attrs[key] = val
		
	def get_attr(self, key):
		return self.attrs[key]
	
	
	def __str__(self):
		ret_str = ''
		for tier in self:
			ret_str += '%s,'%str(tier)
		return '<IGTInstance %s: %s>' % (self.id, ret_str[:-1])
	
	def lang_gold_alignment(self, **kwargs):
		ga = self.glossalign
		la = self.langalign
		
		#=======================================================================
		# If we don't have a language-gloss alignment, assume 1:1, otherwise
		# raise an exception if the lines are of unequal length.
		#=======================================================================
		if not la:
			if len(self.gloss) != len(self.lang):
				raise IGTAlignmentException('Language line and gloss line not the same length at %s' % self._id)
			else:
				return AlignedSent(self.lang, self.trans, ga)
			
		# If we DO have an alignment between language line
		# and translation line...
		else:
			return AlignedSent(self.lang, self.trans, la)
	
	def lang_heuristic_alignment(self, **kwargs):
		ga = self.gloss_heuristic_alignment(**kwargs).aln
		la = self.langalign
		
		#=======================================================================
		# If we don't have a language-gloss alignment, assume 1:1, otherwise
		# raise an exception.
		#=======================================================================
		if not la:
			if len(self.gloss) != len(self.lang):
				raise IGTAlignmentException('Language line and gloss line not the same length at %s' % self._id)
			else:
				return AlignedSent(self.lang, self.trans, ga)

	
	def add_alignment(self, aln, **kwargs):
		'''
		Helper function to insert a given alignment into
		the xigt representation.
		'''
		
		self.gloss.alignment = self.trans.id
		
		
		# Only add this info if we haven't already performed the alignment.
		if not hasattr(self, '_aligned'):
			
			ga_tier = rgx.RGTier(id='ga', type='bilingual-alignments', attributes={'source':self.gloss.id, 'target':self.trans.id})
						
			# Iterate through each gloss and translation word...
			for gw, tw in aln.aligned_words():
				
				aln_item = ga_tier.findAttr('source', gw.id)
				if not aln_item:
					aln_item = rgx.RGItem(id=ga_tier.askItemId(), attributes={'source':gw.id})
					
				if 'target' in aln_item.attributes:
					aln_item.attributes['target'] += ','+tw.id
				else:
					aln_item.attributes['target'] = tw.id
					
				ga_tier.add(aln_item)
									
			self.add(ga_tier)
			
		self._aligned = True
				
	
	def gloss_heuristic_alignment(self, **kwargs):
		'''
		Function to return an AlignedSent object containing the gloss,
		translation, and their Alignment.
		'''
		if hasattr(self, '_gha'):
			gha = self._gha
		else:
			gha = self.gloss_heuristic_alignment_h(**kwargs)
			
		self.add_alignment(gha, **kwargs)
		return gha
	
	def giza_alignment(self, ga, **kwargs):
		asent = ga.force_align(self.gloss.text(), self.trans.text())
		if not asent:
			raise IGTAlignmentException('GIZA did not produce an alignment')
		else:
			return asent[0]
		
	
	def gloss_heuristic_alignment_h(self, **kwargs):
		
		
		gloss = self.gloss
		trans = self.trans
		
		aln = Alignment()
		
		#=======================================================================
		#  1) Get the morphs for each of the tiers
		#
		#  2) Make a first pass, aligning each morph with the first unaligned
		#     morph on the other side.
		#
		#  3) Make subsequent passes to pick up any tokens not aligned. 
		#
		#=======================================================================
		
		if kwargs.get('tokenize', True):
			gloss_tokens = list(gloss.morphs())
			trans_tokens = list(trans.morphs())
		else:
			gloss_tokens = gloss
			trans_tokens = trans

		alignments = get_alignments(gloss_tokens, trans_tokens, **kwargs)
		
		for a, b in alignments:
			aln.add((a, b))
			
			
		#=======================================================================
		# Do the gram matching if it's enabled.
		#=======================================================================
		
		if kwargs.get('grams_on', True):
			kwargs['gloss_on'] = True
			gloss_alignments = get_alignments(gloss_tokens, trans_tokens, **kwargs)
			
			for a, b in gloss_alignments:
				aln.add((a, b))

							
		a = AlignedSent(gloss, trans, aln)
		a.attrs = self.attributes
		self._gha = a
		return a
	

	
	

def get_alignments(gloss_tokens, trans_tokens, iteration=1, **kwargs):
	
	alignments = set([])
		
	# For the second iteration
	if iteration>1:
		gloss_tokens = gloss_tokens[::-1]
		trans_tokens = trans_tokens[::-1]
	
	for gloss_token in gloss_tokens:
		
		for trans_token in trans_tokens:
			
			if gloss_token.morphequals(trans_token, **kwargs):
				# Get the alignment count
				trans_align_count = trans_token.attrs.get('align_count', 0)
				gloss_align_count = gloss_token.attrs.get('align_count', 0)
				
				
				# Only align with tokens 
				if trans_align_count == 0 or kwargs.get('no_multiples', False):
					trans_token.attrs['align_count'] = trans_align_count+1
					gloss_token.attrs['align_count'] = gloss_align_count+1
					alignments.add((gloss_token.index, trans_token.index))
					
					# Stop aligning this gloss token for this iteration.
					break
				
				# If we're on the second pass and the gloss wasn't aligned, align
				# it to whatever remains.
				elif gloss_align_count == 0 and iteration == 2:
					trans_token.attrs['align_count'] = trans_align_count+1
					gloss_token.attrs['align_count'] = gloss_align_count+1
					alignments.add((gloss_token.index, trans_token.index))
				
				
	
	if iteration == 2 or kwargs.get('no_multiples', False):
		return alignments
	else:
		return alignments | get_alignments(gloss_tokens, trans_tokens, iteration+1, **kwargs)
	
		
	

		
class IGTTier(rgx.RGTier):
	'''
	This class is what was originally described as a "Tier" -- a collection of tokens 
	'''
	
	def __init__(self, **kwargs):
		rgx.RGTier.__init__(self, **kwargs)
		
		
		# If we specify content, save this as our string...
		if 'content' in kwargs:
			content = kwargs.get('content')
			assert type(content) == Tokenization, type(content)
			for t in content:
				self.add(t)
		
	
	@classmethod
	def fromString(cls, string, **kwargs):
		'''
		
		Convenience method to create a tier from a string. Helpful for testing.
		
		@param string: whitespace separated string to turn into a tier
		'''
		tier = cls(**kwargs)
		
		for token in tokenize_string(string, tokenizer=whitespace_tokenizer):
			t = IGTToken.fromToken(token)
			tier.append(t)
		return tier
		
	def append(self, item):
		if not isinstance(item, IGTToken):
			raise IGTException('Attempt to add non-IGTToken to IGTTier')
		else:
			rgx.RGTier.add(self, item)
			
	def __str__(self):
		return '<IGTTier type=%s len=%d>' % (self.type, len(self))
	
	def text(self, **kwargs):
		text = ' '.join([token.seq for token in self]).strip()
		if kwargs.get('lowercase', True):
			text = text.lower()
		return text
	
	
	def morphs(self, **kwargs):
		'''
		Return the sequence of morphs for this tier.
		'''
		ret_list = []
		for token in self:
			ret_list.extend(token.morphs(**kwargs))
		return ret_list
	
	# Length
	def __len__(self):
		return len(self._list)
	
	
	def __setitem__(self, k, v):
		self._list[k] = v
		
class Span(object):
	def __init__(self, start, stop):
		self.start = start
		self.stop = stop
		
	def __str__(self):
		return ('%s,%s' % (self.start, self.stop))

class IGTToken(rgx.RGItem, Token):
	
	def __init__(self, content, **kwargs):
		rgx.RGItem.__init__(self, content=content)
		Token.__init__(self, content, **kwargs)
		
		self.attributes['index'] = kwargs.get('index')
		
		
	@classmethod
	def fromToken(cls, token, parent=None):
		return cls(content=token.seq, parent=parent, start=token.start, stop=token.stop, index=token.index)
		
	def split(self):
		return self.get_content.split()
		
	def morphs(self, **kwargs):

		for morph in self.morphed_tokens():
			if kwargs.get('lowercase'):
				morph = Morph(morph.seq.lower(), morph.span, morph.parent)
			yield morph
		
	def morphed_tokens(self):
		morphs = list(tokenize_string(self.get_content(), morpheme_tokenizer))
		
		# If the tokenization yields no tokens, just return the string.
		if self.get_content() and len(morphs) == 0:
			yield Morph(self.get_content(), parent=self)
			
		
		for morph in morphs:
			yield(Morph.fromToken(morph, parent=self))		
		
	
	def __repr__(self):
		return '<IGTToken: [%s] %s>' % (self.index, self.seq)
	
	def __str__(self):
		return self.__repr__()
	
	def lower(self):
		return self.seq.lower()
		
	def text(self, **kwargs):
		text = self.seq
		if kwargs.get('lowercase', True):
			text = text.lower()
		return text
		
	def __hash__(self):
		return id(self)

	
#===============================================================================
# Subclasses of Tiers
#===============================================================================
		
#===========================================================================
# Subclass the RGTier to use for tiers that are specifically intended to
# contain "words"
#===========================================================================
class WordsTier(rgx.RGTier):

	def morphs(self):
		for item in self:
			m_list = tokenize_string(item.get_content(), morpheme_tokenizer)
			
			for m in m_list:

				# Adjust the start-stop indices of the morpheme.
				m.start = m.start + item.start
				m.stop = m.stop + item.start
				
				yield Morph.fromToken(m, item)
				
	def text(self):
		words = [i.get_content() for i in self]
		return ' '.join(words)
			
				
	def __len__(self):
		return len(self._list)
				
#===============================================================================
# LinesTier
#===============================================================================
class LinesTier(IGTTier):
	
	def add_line(self, txt, tag):
		item = rgx.RGItem(id='r%d' % (len(self) + 1), attributes={'tag':tag}, text=txt)
		self.add(item)
	
		
#===============================================================================
# Unit tests
#===============================================================================
		
class MorphTestCase(unittest.TestCase):

	def runTest(self):
		m1 = Morph('the')
		m2 = Morph('dog')
		m3 = Morph('the')
		
		self.assertTrue(m1.morphequals(m3))
		self.assertFalse(m2.morphequals(m1))
		
class IGTTokenTestCase(unittest.TestCase):
	def runTest(self):
		t1 = IGTToken('your')
		t2 = IGTToken('your')
		t3 = IGTToken('you-are')
		t4 = IGTToken('you')
		t5 = IGTToken('Your')
		t6 = IGTToken('1SG.You.ARE')		
		
		self.assertEqual(t1, t2)
		self.assertNotEqual(t1, t3)
		
		self.assertFalse(t4.morphequals(t3))
		self.assertFalse(t3.morphequals(t4))
		self.assertFalse(t3.morphequals(t1))
		self.assertFalse(t5.morphequals(t1, lowercase=False, stem=False))
		self.assertTrue(t5.morphequals(t1, lowercase=True, stem=False))
		self.assertFalse(t6.morphequals(t4, lowercase=True, stem=False))
		
		#=======================================================================
		# Test stemming
		#=======================================================================
		t1 = IGTToken('passed')
		t2 = IGTToken('Pass')
		
		self.assertTrue(t1.morphequals(t2, lowercase=True, stem=True))
		
class MorphTokenCompare(unittest.TestCase):
	def runTest(self):
		t1 = IGTToken('THE.horse')
		m1 = Morph('Horse', parent=t1)
		
		self.assertEqual(m1.parent, t1)
		self.assertFalse(t1.morphequals(m1, lowercase=True, stem=False, deaccent=False))
		self.assertFalse(t1.morphequals(m1, lowercase=False, stem=False))
		self.assertRaises(TokenException, lambda: m1.morphequals('string'))
		self.assertRaises(TokenException, lambda: t1.morphequals('string'))		
		
class AlignGrams(unittest.TestCase):
	def runTest(self):
		o1 = IGTToken('I')
		o2 = IGTToken('1SG')
		
		self.assertTrue(o2.morphequals(o1, gloss_on=True, lowercase=True))
		
class getAlignmentsTest(unittest.TestCase):
	def runTest(self):
		t1 = IGTTier.fromString('This taxi-driver to-me seems to-be tired')
		t2 = IGTTier.fromString("b\"	'This taxi driver seems to me to be tired")
		
		o1 = IGTToken('to-me')
		
		self.assertEquals(get_alignments(t1.morphs(), t2.morphs()), set([(1,2),(2,3),(2,4),(3,6),(3,7),(4,5),(5,8),(5,9),(6,10)]))
		
		t3 = IGTTier.fromString('your house is on your side of the street')
		t4 = IGTTier.fromString('your house is on your side of your street')
		
		self.assertEquals(get_alignments(t3.morphs(), t4.morphs()), {(5, 5), (6, 6), (4, 4), (7, 7), (9, 9), (2, 2), (1, 1), (5, 8), (3, 3)})
		
		t5 = IGTTier.fromString('the dog.NOM ran alongside the other dog')
		t6 = IGTTier.fromString('the dog runs alongside the other dog')
		
		self.assertEquals(get_alignments(t5.morphs(), t6.morphs()), {(1,1), (2,2), (3,3), (4,4), (5, 5), (6, 6), (7, 7)})
		
		t7 = IGTTier.fromString('lizard-PL and gila.monster-PL here rest.PRS .')
		t8 = IGTTier.fromString('The lizards and the gila monsters are resting here .')
		
		self.assertEquals(get_alignments(t7.morphs(), t8.morphs()), {(1,2), (2, 3), (3, 5), (3, 6), (4, 9), (5, 8), (6, 10)})
		
		t10 = IGTTier.fromString('Peter something buy.PRS and something sell.PRS .')
		t9 = IGTTier.fromString('Pedro buys and sells something .')
		
		
		self.assertEquals(get_alignments(t10.morphs(), t9.morphs()), {(2,5), (3,2), (4,3), (5, 5), (6, 4), (7, 6)})
		
		
class AlignContains(unittest.TestCase):
	def runTest(self):
		a1 = Alignment([(2, 5), (3, 4), (1, 1), (4, 3)])
		
		self.assertTrue(a1.contains_src(2))
		self.assertTrue(a1.contains_src(4))
		