'''
Created on Jan 31, 2014

@author: rgeorgi
'''
from treebanks.TextParser import TextParser
from utils.ConfigFile import ConfigFile
import argparse
from transliteration import *
import os
import sys

class ConllParser(TextParser):
	'''
	Text parser for the google universal treebank.
	'''
	
	
	def parse(self):
		c = ConfigFile(self.conf)
		
		root = c['root']
		outdir = c['outdir']
		testfile = c['testfile']
		trainfile = c['trainfile']
		goldfile = c['goldfile']
		split = float(c['trainsplit'])
		maxlength = c['maxLength']
		rawfile = c['rawfile']
		delimeter = c['delimeter']
		translit = eval(c['translit'])
		limit = int(c['sentence_limit'])
		
		f = file(root, 'r')
		
		gold_sent = ''
		raw_sent = ''
		
		raw_sents = []
		gold_sents = []
		test_sents = []
		
		train_f = file(os.path.join(outdir, trainfile), 'w')		
		gold_f = file(os.path.join(outdir, goldfile), 'w')
		test_f = file(os.path.join(outdir, testfile), 'w')
		raw_f = file(os.path.join(outdir, rawfile), 'w')
		
		if split:
			splitnum = int(limit * split / 100)
		else:
			splitnum = 0
		
		raw_out = raw_f
		tagged_out = train_f		
		
		i = 0
		for line in f:
			
			if i == splitnum:
				raw_out.close(), tagged_out.close()
				
				raw_out = test_f
				tagged_out = gold_f		
			
			line.split()
			
			if not line.strip() and gold_sent:
				raw_sents.append(raw_sent.strip())
				gold_sents.append(gold_sent.strip())
				
				tagged_out.write(gold_sent.strip()+'\n')
				raw_out.write(raw_sent.strip()+'\n')				
								
				i+= 1
				gold_sent = ''
				raw_sent = ''
				if i > limit:
					break

			elif line.strip():
				id, form, lemma, cpostag, postag, feats, head, deprel, phead, pdeprel = line.split()
				if translit:
					form = translit.translit(form).lower()
					
				gold_sent += '%s%s%s ' % (form, delimeter, cpostag)
				raw_sent += '%s ' % form
				
			
			
							
		raw_out.close(), tagged_out.close()
		sys.stdout.write('%d sents written' % len(gold_sents))
			
					
					
					
		
	
if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('conf', metavar='CONF')
	
	args = p.parse_args()
	
	cp = ConllParser(args.conf)
	cp.parse()