'''
Created on Mar 11, 2014

@author: rgeorgi
'''

import re

#===============================================================================
# Sub-tasks of cleaning
#===============================================================================

punc_re = '[.?!,\xc2]'

def grammaticality(string):
	# Now, remove leading grammaticality markers
	return re.sub('^[\*\?]+', '', string).strip()

def surrounding_quotes_and_parens(ret_str):
	ret_str = re.sub('^[\'"`\[\(]+', '', ret_str).strip()
	ret_str = re.sub('[\'"`\]\)\.]+$', '', ret_str).strip()
	return ret_str

def split_punctuation(ret_str):
	return re.sub(r'(\w+)([.?!,])+', r'\1 \2', ret_str).strip()

def remove_external_punctuation(ret_str):
	ret_str = re.sub(r'(\w+)({})+\s'.format(punc_re), r'\1 ', ret_str).strip()
	ret_str = re.sub(r'(?:^|\s)({}+)(\w+)'.format(punc_re), r'\2', ret_str).strip()
	return re.sub(r'(\w+)([{}])+$'.format(punc_re), r'\1 ', ret_str).strip()

def remove_solo_punctuation(ret_str):
	ret_str = re.sub('\s*{}+\s*'.format(punc_re), '', ret_str)
	return ret_str


def rejoin_letter(ret_str, letter='t', direction='right'):
	'''
	Reattach lone letters hanging out by their lonesome.
	@param ret_str:
	'''
	if direction == 'right':
		ret_str = re.sub(r'\s(%s)\s+(\S+)'%letter, r' \1\2', ret_str).strip()
	elif direction == 'left':
		ret_str = re.sub(r'(\S+)\s+(%s)\s'%letter, r'\1\2 ', ret_str).strip()
	else:
		raise Exception('Wrong direction specified!')
	return ret_str

def remove_byte_char(ret_str):
	return re.sub('^b["\']\s+', '', ret_str).strip()

def remove_parenthetical_numbering(ret_str):
	return re.sub('^\S+\s*[.)]', '', ret_str).strip()

def remove_period_numbering(ret_str):
	return re.sub('^\S+\s*[.)]', '', ret_str).strip()

def remove_numbering(ret_str):
	ret_str = remove_parenthetical_numbering(ret_str)
	ret_str = remove_period_numbering(ret_str)
	return ret_str

#===============================================================================
# Different tiers of cleaning
#===============================================================================

def clean_gloss_string(ret_str):
	# Rejoin letters
	ret_str = rejoin_letter(ret_str, 't', 'right')
	ret_str = rejoin_letter(ret_str, 'h', 'left')
	
	# Remove word-final punctuation
	ret_str = remove_external_punctuation(ret_str)
	
	return ret_str

def clean_trans_string(string):
	# Start by removing the leading "B" stuff
	ret_str = re.sub('^b["\']', '', string).strip()
	
	# Remove word-final punctuation:
	ret_str = remove_external_punctuation(ret_str)
	
	# Remove solo punctuation
	ret_str = remove_solo_punctuation(ret_str)
	
	# Remove surrounding quotes and parentheticals
	ret_str = surrounding_quotes_and_parens(ret_str)
	
	# Remove leading grammaticality markers
	ret_str = grammaticality(ret_str)
	
	# Remove surrounding quotes and parentheticals
	ret_str = surrounding_quotes_and_parens(ret_str)

	
	# t seems to hang out on its own
	ret_str = rejoin_letter(ret_str, letter='t', direction='right')
	ret_str = rejoin_letter(ret_str, letter='h', direction='left')
	ret_str = rejoin_letter(ret_str, letter='e', direction='left')
	
	
	# Remove leading numbering
	ret_str = remove_numbering(ret_str)
	
	return ret_str

def clean_lang_string(ret_str):
	# Remove leading byte string
	ret_str = remove_byte_char(ret_str)
	
	# First remove leading parenthetical numbering
	ret_str = remove_numbering(ret_str)
	
	# Now, remove leading grammaticality markers
	ret_str = grammaticality(ret_str)
	
	# Remove spurious brackets
	ret_str = re.sub('[\[\]\(\)]', '', ret_str).strip()
	
	# Split punctuation
	ret_str = remove_external_punctuation(ret_str)
	

	return ret_str