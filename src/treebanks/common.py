'''
Created on Oct 22, 2013

@author: rgeorgi
'''
import os
import codecs

def raw_writer(path, lines):
	f = codecs.open(path, 'w', encoding='utf-8')
	for line in lines:
		f.write('%s\n' % line)
	f.close()


def write_files(outdir, split, testfile, trainfile, goldfile, remappedfile, all_sents, gold_sents, remapped_sents):
	# Split the data into train and test.
	train_idx = int(len(all_sents) * (float(split)/100))
	train_sents = all_sents
	test_sents = all_sents
	gold_out = gold_sents
	remapped_out = remapped_sents
	
	raw_writer(os.path.join(outdir, testfile), test_sents)
	raw_writer(os.path.join(outdir, trainfile), train_sents)
	raw_writer(os.path.join(outdir, goldfile), gold_out)
	if remappedfile:
		raw_writer(os.path.join(outdir, remappedfile), remapped_out)
	

def process_tree(t, delimeter, maxlength = 0, tm = None):
	leaves = t.leaves()
	if maxlength and (len(leaves) > maxlength):
		return (None, None, None)
	else:
		sent_str = ''
		gold_str = ''
		remapped_str = ''
		
		for leaf in leaves:
			if not leaf.pos.strip():
				continue
			
			# Add the token to the sentences
			sent_str += '%s ' % leaf.label
			gold_str += '%s%s%s ' % (leaf.label, delimeter, leaf.pos)
			if tm:
				newtag = tm[leaf.pos]
				remapped_str += '%s%s%s ' % (leaf.label, delimeter, newtag)
			
		return (sent_str.strip(), gold_str.strip(), remapped_str.strip())