'''
Created on Mar 11, 2014

@author: rgeorgi
'''

import sys, re
import unittest
import string

#===============================================================================
# Sub-tasks of cleaning
#===============================================================================

punc_re = '[.?!,\xc2]'
list_re = '(?:[0-9]+|[a-z]|i+)'

def grammaticality(string):
	# Now, remove leading grammaticality markers
	return re.sub('[#\*\?]+', '', string).strip()

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

def remove_elipses(ret_str):
	return re.sub('\.\s*\.\s*\.', '', ret_str)

def remove_solo_punctuation(ret_str):
	ret_str = re.sub('\s*{}+\s*'.format(punc_re), '', ret_str)
	return ret_str

def remove_final_punctuation(ret_str):
	ret_str = re.sub('{}+$'.format(punc_re), '', ret_str.strip())
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
		raise Exception('Invalid direction specified!')
	return ret_str

def remove_byte_char(ret_str):
	return re.sub('^b["\']\s+', '', ret_str).strip()

def remove_parenthetical_numbering(ret_str):
	return re.sub('^\S+\s*[.)]', '', ret_str).strip()

def remove_period_numbering(ret_str):
	'''
	Remove period-initial numbering like:
	|
	1.   a.  ii.
	'''
	number_search = '^%s\.' % list_re
	
	number_match = re.search(number_search, ret_str.strip())
	
	if number_match:
		return re.sub(number_search, '', ret_str)
	else:
		return ret_str

def remove_leading_numbers(ret_str):
	return re.sub('^[0-9]+', '', ret_str).strip()

def remove_numbering(ret_str):
	ret_str = remove_parenthetical_numbering(ret_str)
	ret_str = remove_period_numbering(ret_str)
	ret_str = remove_leading_numbers(ret_str)
	return ret_str

def remove_hyphens(ret_str):
	return re.sub('[\-\=]', '', ret_str)

def remove_leading_punctuation(ret_str):
	return re.sub('^[%s]+' % string.punctuation, '', ret_str)

def collapse_spaces(ret_str):
	return re.sub('\s+', ' ', ret_str)

def merge_lines(linelist):
	
	# TODO: Verify merge_lines is working...
	
	'''
	Given two lines, merge characters that fall into blank space on
	the other line.
	
	@param linelist:
	'''
	
	newline = ''
	blank_spans = []
	for line in linelist:
		
		# If this is the first line, just make it the newline
		if not newline:
			newline = line[:]
			
			# Find all the blanks in the newline
			blanks = re.finditer('\s+', newline)
			for blank in blanks:
				blank_spans.append(blank.span())
							
		# If there is already a newline, look at the non-blank
		# parts of this line and insert them.
		else:
			nonblanks = re.finditer('\S+', line)
			for nonblank in nonblanks:
				nonblank_start, nonblank_stop = nonblank.span()
				nonblank_txt = nonblank.group(0)

				#===============================================================
				# If the nonblank occurs after the end of the original line..
				#===============================================================
				if nonblank_start >= len(newline):						
					oldline = newline[:]
					newline = ''
					
					for i in range(len(line)):
						if i < nonblank_start and i < len(oldline):
							newline += oldline[i]
						elif i < nonblank_start and i >= len(oldline):
							newline += ' '
						else:
							newline += line[i]
					continue
				
				#===============================================================
				# Otherwise, look to see if it can fit inside a blank space.
				#===============================================================

				fits = False
				for blank_start, blank_stop in blank_spans:
					if nonblank_start >= blank_start and nonblank_stop <= blank_stop:
						fits = True
						break
						
				if fits:
					# Actually merge the strings
					oldline = newline[:] # Copy the old string
					newline = ''
					
					for i in range(len(oldline)):
						if i >= nonblank_start and i < nonblank_stop:
							newline += nonblank_txt[i-nonblank_start]
						else:
							newline += oldline[i]
				

								
				
				
		
					# Find all the blanks in the newline
					blank_spans = []
					blanks = re.finditer('\s+', newline)
					for blank in blanks:
						blank_spans.append(blank.span())
			
	return newline
	
	

#===============================================================================
# Different tiers of cleaning
#===============================================================================

def clean_gloss_string(ret_str):
	
	# Remove ellipses
	#ret_str = remove_elipses(ret_str) 
	
	# Rejoin letters
	ret_str = rejoin_letter(ret_str, 't', 'right')
	ret_str = rejoin_letter(ret_str, 'h', 'left')
	
	# Remove word-final punctuation
	ret_str = remove_external_punctuation(ret_str)
	
	# Collapse spaces
	ret_str = collapse_spaces(ret_str)
	
	# Remove final punctuation
	ret_str = remove_final_punctuation(ret_str)
	
	# Remove illegal chars
	ret_str = re.sub('#', '', ret_str)
	
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
	
	# Collapse spaces
	ret_str = collapse_spaces(ret_str)
	
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
	ret_str = split_punctuation(ret_str)
	
	# Collapse spaces
	ret_str = collapse_spaces(ret_str)
	
	# Remove final punctuation
	ret_str = remove_final_punctuation(ret_str)
	
	
	#ret_str = remove_hyphens(ret_str)

	return ret_str

#===============================================================================
# Backoff methods
#===============================================================================

def hyphenate_infinitive(ret_str):
	return re.sub('to\s+(\S+)', r'to-\1', ret_str, flags=re.I)

#===============================================================================
# Test Cases
#===============================================================================

class TestLangLines(unittest.TestCase):
	
	def runTest(self):
		
		l1 = '  (38)     Este taxista     (*me) parece [t estar cansado]'
		l1c = 'Este taxista *me parece t estar cansado'
		
		self.assertEqual(clean_lang_string(l1), l1c)
		
	def keep_something_test(self):
		l1 = ' (1)      Mangi-a.'
		#l1 = '  (1)     Mangi-a.'
		
		l1_clean = clean_lang_string(l1)
		l1_target = 'Mangi-a'
		
		print(l1_clean == l1_target)
		
		self.assertEquals(l1_clean, l1_target)
		
class TestHyphenate(unittest.TestCase):
	def runTest(self):
		h1 = 'the guests wanted to visit the other pavilion'
		h1f ='the guests wanted to-visit the other pavilion'
		
		self.assertEqual(hyphenate_infinitive(h1), h1f)
		

		
		