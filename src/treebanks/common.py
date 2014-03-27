'''
Created on Oct 22, 2013

@author: rgeorgi
'''
import os
import codecs
import re
import sys

def raw_writer(path, lines):
	f = codecs.open(path, 'w', encoding='utf-8')
	for line in lines:
		f.write('%s\n' % line)
	f.close()
	
def mallet_writer(path, lines, delimeter = '/', lowercase = True):
	f = codecs.open(path, 'w', encoding='utf-8')
	for line in lines:
		
		if lowercase:
			line = unicode.lower(line)
		
		for token in line.split():
			if len(token.split(delimeter)) == 2:
				word, tag = token.split(delimeter)
				f.write('%s %s\n' % (word, tag))
			else:
				f.write('%s\n' % token)
				
		# Write a blank line in between sentences
		f.write('\n')
	f.close()


def traintest_split(sentlist, split):
	train_idx = int(len(sentlist) * (float(split)/100))
	return (sentlist[:train_idx], sentlist[train_idx:])

def write_mallet(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents, full_file = None, lowercase = True):
	train, test = traintest_split(all_sents, split)
	gold_train, gold_test = traintest_split(gold_sents, split)
	
	mallet_writer(os.path.join(outdir, testfile), test, lowercase = lowercase)
	mallet_writer(os.path.join(outdir, trainfile), gold_train, lowercase = lowercase)
	mallet_writer(os.path.join(outdir, goldfile), gold_test, lowercase = lowercase)
	

def write_files(outdir, split, testfile, testtagged, trainfile, traintagged, all_sents, gold_sents):
	# Split the data into train_raw and test_raw.
	train_raw, test_raw = traintest_split(all_sents, split)
	train_tagged, test_tagged = traintest_split(gold_sents, split)
	
	raw_writer(os.path.join(outdir, testfile), test_raw)
	raw_writer(os.path.join(outdir, trainfile), train_raw)
	
	raw_writer(os.path.join(outdir, testtagged), test_tagged)
	raw_writer(os.path.join(outdir, traintagged), train_tagged)
	
	

def process_tree(t, delimeter, maxlength = 0, tm = None, simplify = False, keep_traces = False, lowercase=False):
	treepos = t.pos()
	
	if maxlength and (len(treepos) > maxlength):
		return (None, None)
	else:
		sent_str = ''
		gold_str = ''
		
		for word, pos in treepos:
			if simplify:
				pos = pos.split('-')[0]
			
			if not pos.strip() or re.match('(?:-NONE-)|^\*', pos.strip()):
				continue
			
			if lowercase:
				word = word.lower()
			# Add the token to the sentences
			sent_str += '%s ' % word		
			if tm:
				newtag = tm[pos]
				gold_str += '%s%s%s ' % (word, delimeter, newtag)
			else:
				gold_str += '%s%s%s ' % (word, delimeter, pos)
			
		return (sent_str.strip(), gold_str.strip())