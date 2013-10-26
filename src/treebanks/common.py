'''
Created on Oct 22, 2013

@author: rgeorgi
'''
import os
import codecs
import re

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

	

def process_tree(t, delimeter, maxlength = 0, tm = None):
	leaves = t.leaves()
	if maxlength and (len(leaves) > maxlength):
		return (None, None)
	else:
		sent_str = ''
		gold_str = ''
		
		for leaf in leaves:
			if not leaf.pos.strip() or re.match('\*[^\*]+\*', leaf.pos.strip()):
				continue
			
			# Add the token to the sentences
			sent_str += '%s ' % leaf.label			
			if tm:
				newtag = tm[leaf.pos]
				gold_str += '%s%s%s ' % (leaf.label, delimeter, newtag)
			else:
				gold_str += '%s%s%s ' % (leaf.label, delimeter, leaf.pos)
			
		return (sent_str.strip(), gold_str.strip())