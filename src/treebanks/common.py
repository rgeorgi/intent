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


def traintest_split(sentlist, split):
	train_idx = int(len(sentlist) * (float(split)/100))
	return (sentlist[:train_idx], sentlist[train_idx:])

def write_files(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents, full_file = None):
	# Split the data into train and test.
	train, test = traintest_split(all_sents, split)
	gold_train, gold_test = traintest_split(gold_sents, split)
	
	raw_writer(os.path.join(outdir, testfile), test)
	raw_writer(os.path.join(outdir, trainfile), gold_train)
	raw_writer(os.path.join(outdir, goldfile), gold_test)
	
	if full_file:
		raw_writer(os.path.join(outdir, full_file), all_sents)

	

def process_tree(t, delimeter, maxlength = 0, tm = None, simplify = False, keep_traces = False):
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
			
			# Add the token to the sentences
			sent_str += '%s ' % word		
			if tm:
				newtag = tm[pos]
				gold_str += '%s%s%s ' % (word, delimeter, newtag)
			else:
				gold_str += '%s%s%s ' % (word, delimeter, pos)
			
		return (sent_str.strip(), gold_str.strip())