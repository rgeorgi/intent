'''
Created on Oct 2, 2014

@author: rgeorgi
'''
import sys, logging

ALIGN_LOGGER = logging.getLogger('projection')

class ProjectEval(object):
	'''
	classdocs
	'''


	def __init__(self, aligned_corpus, name=''):
		'''
		Constructor
		'''
		self.corpus = aligned_corpus
		
		self.name = name
		if name:
			self.name = '%s: ' % name
		
	def eval(self):
		
		gold_matches = 0
		gold_compares = 0
		
		auto_matches = 0
		auto_compares = 0
		
		lang_tokens = 0
		
		# For each aligned sentence in the corpus
		for aligned_sent in self.corpus:
			
			# Iterate through each source (gloss) token
			for src_token in aligned_sent.src_tokens:
				
				# Get the target indices with which the 
				tgt_indices = aligned_sent.src_to_tgt(src_token.index)
				
				# We will try to score based on the assigned (taglabel) tags
				# as well as the gold (goldlabel) tags
				auto_tgt_tags = [aligned_sent.get_tgt(t).taglabel for t in tgt_indices]
				gold_tgt_tags = [aligned_sent.get_tgt(t).goldlabel for t in tgt_indices]
				
				# If there is "NONE" in the target tags,
				# that means they haven't been tagged, so
				# Let's not count this against the alg.
				if None not in auto_tgt_tags:
				
					# Very liberal scoring, if the gold label is among
					# either of the projected labels, assign it.
					if src_token.goldlabel in auto_tgt_tags:
						auto_matches += 1
					
					auto_compares += 1
					
				if None not in gold_tgt_tags:
					if src_token.goldlabel in gold_tgt_tags:
						gold_matches += 1
				
					gold_compares += 1

			# Count the number of lang tokens here
			lang_tokens += len(aligned_sent.tgt_tokens)
					
		ALIGN_LOGGER.log(logging.INFO,'%s%d,%d,%d,%d,%d' % (self.name, auto_matches, auto_compares, gold_matches, gold_compares, lang_tokens))
				