'''
Created on Mar 8, 2014

@author: rgeorgi
'''
import sys
from utils.argutils import ArgPasser
import re
import logging
import utils.token


#===============================================================================
# Initialize logging
#===============================================================================

MODULE_LOGGER = logging.getLogger(__name__)

gramdict = {'1sg':['i','me'],
		'det':['the'],
		'3pl':['they'],
		'3sg':['he','she', 'him', 'her'],
		'3sgf':['she','her'],
		'2sg':['you'],
		'3sgp':['he'],
		'poss':['his','her','my', 'their'],
		'neg':["n't",'not'],
		'2pl':['you']}

def sub_grams(gram):
	if gram in gramdict:
		return gramdict[gram]
	else:
		return [gram]
	
#===============================================================================
# Write Gram
#===============================================================================

def write_gram(token, **kwargs):
	
	# Re-cast the kwargs as an argpasser.
	kwargs = ArgPasser(kwargs)
	
	type = kwargs.get('type')
	output = kwargs.get('output', sys.stdout)
	
	posdict = kwargs.get('posdict', {})	
		
	# Previous tag info
	prev_gram = kwargs.get('prev_gram')
	next_gram = kwargs.get('next_gram')
	
	# Get heuristic alignment
	aln_labels = kwargs.get('aln_labels', [])

	#===========================================================================
	# Break apart the token...
	#===========================================================================
	gram = token.seq
		
	pos = token.goldlabel

	# Lowercase if asked for	
	lower = kwargs.get('lowercase', True, bool)
	gram = gram.lower() if gram else gram
		
	# Output the grams for a classifier
	if type == 'classifier' and pos:
		output.write(pos)
		
		#=======================================================================
		# Get the morphemes
		#=======================================================================
		morphs = utils.token.tokenize_string(gram, utils.token.morpheme_tokenizer)
		
		#=======================================================================
		# Is there a number
		#=======================================================================
		if re.search('[0-9]', gram) and kwargs.get('feat_has_number', False, bool):
			output.write('\thas-number:1')
			
		#=======================================================================
		# What labels is it aligned with
		#=======================================================================
		if kwargs.get('feat_align', False, bool):
			for aln_label in aln_labels:
				output.write('\taln-label-%s:1' % aln_label)
			
		#=======================================================================
		# Suffix
		#=======================================================================
		if kwargs.get('feat_suffix', False, bool):
			output.write('\tgram-suffix-3-%s:1' % gram[-3:].replace(':','-'))
			output.write('\tgram-suffix-2-%s:1' % gram[-2:].replace(':','-'))
			output.write('\tgram-suffix-1-%s:1' % gram[-3:].replace(':','-'))
			
		#=======================================================================
		# Prefix
		#=======================================================================
		if kwargs.get('feat_prefix', False, bool):
			output.write('\tgram-prefix-3-%s:1' % gram[:3].replace(':','-'))
			output.write('\tgram-prefix-2-%s:1' % gram[:2].replace(':','-'))
			output.write('\tgram-prefix-1-%s:1' % gram[:1].replace(':','-'))
			
		#=======================================================================
		# Number of morphs
		#=======================================================================		
		if kwargs.get('feat_morph_num', False, bool):
			output.write('\t%d-morphs:1' % len(morphs))
	
		
		#===================================================================
		# Previous gram
		#===================================================================
		if prev_gram:
			prev_gram = prev_gram.seq
			prev_gram = prev_gram.lower() if lower else prev_gram
					
			# And then tokenize...
			for token in utils.token.tokenize_string(prev_gram, utils.token.morpheme_tokenizer):
				
				if kwargs.get('feat_prev_gram', False, bool):
					output.write('\tprev-gram-%s:1' % token.seq)
								
				# Add prev dictionary tag
				if kwargs.get('feat_prev_gram_dict', False, bool) and token.seq in posdict:
					prev_tags = posdict.top_n(token.seq)
					output.write('\tprev-gram-dict-tag-%s:1' % prev_tags[0][0])
					
		#===================================================================
		# Next gram
		#===================================================================
		if next_gram:
			next_gram_seq = next_gram.seq
			next_gram_seq = next_gram_seq.lower() if lower else next_gram_seq
			for token in utils.token.tokenize_string(next_gram_seq, utils.token.morpheme_tokenizer):
				
			#===================================================================
			# Gram itself
			#===================================================================
			
				if kwargs.get('feat_next_gram', False, bool):				
					output.write('\tnext-gram-%s:1' % token.seq)
				
				if kwargs.get('feat_next_gram_dict', False, bool) and token.seq in posdict:
					next_tags = posdict.top_n(token.seq)
					output.write('\tnext-gram-dict-tag-%s:1' % next_tags[0][0])
		
		#=======================================================================
		# Iterate through the morphs
		#=======================================================================
		
		for token in morphs:
			#===================================================================
			# Just write the morph
			#===================================================================
			if kwargs.get('feat_basic', False, bool):
				output.write('\t%s:1' % token.seq)
			
			#===================================================================
			# If the morph resembles a word in our dictionary, give it
			# a predicted tag
			#===================================================================
			
			if token.seq in posdict and kwargs.get('feat_dict', False, bool):
				
				top_tags = posdict.top_n(token.seq)
				best = top_tags[0][0]
				if best != pos:
					MODULE_LOGGER.debug('%s TAGGED as %s NOT %s' % (gram, pos, best))
				
				output.write('\ttop-dict-word-%s:1' % top_tags[0][0])
				if len(top_tags) > 1:
					output.write('\tnext-dict-word-%s:1' % top_tags[1][0])
				

		output.write('\n')
				
	if type == 'tagger':
		output.write('%s/%s ' % (gram, pos))