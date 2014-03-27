'''
Created on Jan 31, 2014

@author: rgeorgi
'''
from treebanks.TextParser import TextParser
from utils.ConfigFile import ConfigFile
import argparse
import os
import sys
from corpora.POSCorpus import POSCorpus, POSToken, POSCorpusInstance

def sent_count(path):
	f = open(path, 'r')
	sent_count = 0
	
	state = 'out'
	for line in f:
		if state == 'out' and line.strip():
			state = 'in'
			sent_count += 1
		elif not line.strip():
			state = 'out'
	return sent_count

class ConllParser(TextParser):
	'''
	Text parser for the google universal treebank.
	'''
	
	
	def parse_file(self, **kwargs):
		
		root = kwargs.get('root')
			
		outdir = kwargs.get('outdir')
		testfile = kwargs.get('testfile')
		trainfile = kwargs.get('trainfile')
		goldfile = kwargs.get('goldfile')
		split = int(kwargs.get('trainsplit', 90))
		maxlength = kwargs.get('maxlength')
		rawfile = kwargs.get('rawfile')
		delimeter = kwargs.get('delimeter', '/')
						
		
		
		num_sents = sent_count(root)
		limit = kwargs.get('sentence_limit', num_sents)

		f = open(root, 'r')
		
		os.makedirs(outdir, exist_ok=True)
		
		if split:
			splitnum = int(limit * split / 100)
		else:
			splitnum = 0
		
		if splitnum != 0:
			
			train_f = open(os.path.join(outdir, trainfile), 'w')		
			raw_f = open(os.path.join(outdir, rawfile), 'w')
			untagged_out = raw_f
			tagged_out = train_f		

		
			
		written = 0
		
		# Keep data in the corpus
		corpus = POSCorpus()
		
		#=======================================================================
		# Iterate through the lines in the CONLL file.
		#=======================================================================
		
		i = 0
		inst = POSCorpusInstance()
		for line in f:
			
			#===========================================================
			# Once we've run through all the testing instances, start
			# writing to the training instances.
			#===========================================================
			if i == splitnum:				
				untagged_out = open(os.path.join(outdir, testfile), 'w')
				tagged_out = open(os.path.join(outdir, goldfile), 'w')
			
			#===================================================================
			# If it's not a blank line, add it to the current instance.
			#===================================================================
			
			if line.strip():
				index, form, lemma, cpos, postag, feats, head, deprel, phead, pdeprel = line.split()
				t = POSToken(form, cpos, int(index))
				t.finepos = postag
				inst.append(t)

			else:				
				if len(inst) > 0:
					corpus.append(inst)
					untagged_out.write(inst.raw(lowercase=True)+'\n')
					tagged_out.write(inst.slashtags(delimeter, lowercase=True)+'\n')
					written += 1
				i+=1
					
				inst = POSCorpusInstance()
			
			if written > limit:
				break

				
			
		
							
		untagged_out.close(), tagged_out.close()
		sys.stdout.write('%d sents written\n' % (len(corpus)))
		return corpus		
			
					
					
					
		
	
if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('conf', metavar='CONF')
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	

	
	if c.get('train_root') and c.get('test_root'):
		cp = ConllParser()
		c['root'] = c.get('train_root')
		c['trainsplit'] = 100
		corp = cp.parse_file(**c)
		
		cp = ConllParser()
		c['root'] = c.get('test_root')
		c['trainsplit'] = 0
		corp = cp.parse_file(**c)
		
	elif c.get('root'):
		cp = ConllParser()
		corp = cp.parse_file(**c)