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


def write_files(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents, full_file = None):
	# Split the data into train and test.
	train_idx = int(len(all_sents) * (float(split)/100))
	train_sents = gold_sents[:train_idx]
	test_sents = all_sents[train_idx:]
	gold_out = gold_sents[train_idx:]
	
	raw_writer(os.path.join(outdir, testfile), test_sents)
	raw_writer(os.path.join(outdir, trainfile), train_sents)
	raw_writer(os.path.join(outdir, goldfile), gold_out)
	
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