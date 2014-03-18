'''
Created on Feb 28, 2014

@author: rgeorgi
'''

import os, sys, re, pickle, argparse

#===============================================================================
# IGT Cleaning Methods 
#
#===============================================================================

def tokenize(line, punctuation = True, morphemes = True):
	if punctuation:
		line = re.sub('([\?\.\!]*)', '\1', line)
		
	if morphemes:
		line = re.sub('[-\.]', ' ', line)
		
	return line
		
	
	

paren_re = re.compile(r'\([^)]*\)')
paren_num_re = re.compile(
	r"^\(\s*(" # start (X; ( X; group for alternates
	r"[\d.]+\w?|\w|" # 1 1a 1.a 1.23.4b; a b (no multiple chars, except...)
	r"[ivxlc]+)"	# roman numerals: i iv xxiii; end alt group
	r"['.:]*\s*\)[.:]*") # optional punc (X) (X:) (X') (X.) (X. ) (X). (X):
num_re = re.compile(
	r"([\d.]+\w?|\w|[ivxlc]+)" # nums w/no parens; same as above
	r"['.):]+\s") # necessary punc; 1. 1' 1) 1: 10.1a. iv: etc.
precontent_re = re.compile(r'^\s*\w+(\s\w+)?:\s')

def normalize_line(line):
	if line is None or line.strip() == '': return None
	# remove spaces, quotes, and punctuation to make later regexes simpler
	line = line.strip().strip('"\'`')
	# only strip initial parens if on both sides (so we don't turn 'abc (def)'
	# into 'abc (def'
	if line.startswith('(') and line.endswith(')'): line = line[1:-1]
	# one more space, quote, and punc strip, in case the parens grouped them
	line = line.strip().strip('"\'`')
	# re-add a period (to all lines)
	# remove inner parens (with encapsulated content)
	# this seems to to go too far in some cases, see ace.item11
	line = paren_re.sub('', line)
	# IGT-initial numbers (e.g. '1.' '(1)', '5a.', '(ii)')
	line = paren_num_re.sub('', line)
	line = num_re.sub('', line)
	# precontent tags can be 1 or 2 words ("intended:" or "speaker", "a:")
	# ignore those with 3 or more
	line = precontent_re.sub('', line)
	# ignore ungrammatical or questionably lines or those with alternates
	# now we want to include these, separate out the # or * and mark the
	# judgments  for /, it's no longer a bother 
	# do this later anyway
	# if line.startswith('*') or line.startswith('#'): or '/' in line:
	#	return None
	
	line = re.sub('[\'\"\`]*', '', line)
	return line

#===============================================================================
# MAIN FUNCTION 
#
#===============================================================================

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-r', '--raw')
	
	args = p.parse_args()
		
	
	if args.raw:
		
		# -- 1) Slight shortcut here, loading the processed corpus from pickle.
		p_path = os.path.join(args.raw, 'corpus.pkl')
# 		pickle.dump(xc, open(p_path, 'wb'))
		xc = pickle.load(open(p_path, 'rb'))
		
		gloss_path = os.path.join(args.raw, 'gloss.txt')
		trans_path = os.path.join(args.raw, 'trans.txt')
		
		gloss_f = open(gloss_path, 'w')
		trans_f = open(trans_path, 'w')
		
		for igt in xc.igts:
			clean = igt.get('c')
			
			glosses = []
			translations = []
			
			for item in clean.items:
				tags = item.attributes.get('tag','').split('+')
				if 'G' in tags:
					glosses.append(item.content)
				elif 'T' in tags:
					translations.append(item.content)
					
					
			if glosses and translations:
				gloss = glosses[0]
				trans = translations[0]
				
				# Do the initial cleaning.
				gloss = normalize_line(gloss)
				trans = normalize_line(trans)
				
				gloss = tokenize(gloss)
				trans = tokenize(trans)
				
				gloss = gloss.lower()
				trans = trans.lower()
				
				gloss_f.write(gloss+'\n')
				trans_f.write(trans+'\n')
				
				gloss_f.flush()
				trans_f.flush()
				
		gloss_f.close(), trans_f.close()