'''
Created on Feb 14, 2014

@author: rgeorgi
'''
from treebanks.TextParser import TextParser
from utils.ConfigFile import ConfigFile
import argparse
import re
import sys

from eval.align_eval import aer, AlignEval

import pickle
import os

from alignment.Alignment import Alignment, AlignedSent, AlignedCorpus
from alignment.align import heuristic_align, heuristic_align_corpus
from corpora.POSCorpus import POSCorpus
from utils.encodingutils import getencoding
import codecs


class NAACLParser(TextParser):
	
	def __init__(self, conf):
		self.conf = ConfigFile(conf)
		
	def get_corpus(self):
		sents = self.get_sents()
		ha_sents = heuristic_align_corpus(sents, lowercase=False, remove_punc = True, stem=True)
		
		c = self.conf
		outdir = c['outdir']
		
		gloss_path = os.path.join(outdir, 'naacl_gloss.txt')
		trans_path = os.path.join(outdir, 'naacl_trans.txt')
		aln_path = os.path.join(outdir, 'naacl_aln.txt')
		ha_gloss = os.path.join(outdir, 'ha_gloss.txt')
		ha_trans = os.path.join(outdir, 'ha_trans.txt')
		
		
		sents.write(gloss_path, trans_path, aln_path)
		
				
		ha = heuristic_align_corpus(sents, lowercase=True, remove_punc=True, stem=True, morph_on=True)
		ha2 = heuristic_align_corpus(sents, lowercase=True, remove_punc=True, stem=True, morph_on=True, aln_direction='b')
		
		
		
		ha_gloss_f = open(ha_gloss, 'w')
		ha_trans_f = open(ha_trans, 'w')
		
		for asent in ha:
			for gloss_w, trans_w in asent.aligned_words():
				ha_gloss_f.write(gloss_w+'\n')
				ha_trans_f.write(trans_w+'\n')
		
		ha_gloss_f.close(), ha_trans_f.close()
		
		ae = AlignEval(ha, sents)
		ae2 = AlignEval(ha2, sents)
		
		print(ae.all())
		print(ae2.all())
		
				
		
	def get_sents(self):
		c = self.conf
		
		corpus = POSCorpus()
		
		sents = AlignedCorpus()
		
		for root in c['roots'].split(','):
			
			encoding = getencoding(root.strip())			
			
			f = codecs.open(root.strip(), encoding=encoding)
			data = f.read()
			f.close()
			
			print data
			sys.exit()
			
			gloss_aligns = re.findall('Q5:[^\n]+\n(.+?)\n(.+?)\n[\s\n]+([0-9][\s\S]+?)######## Q5', data)
			
			for gloss, trans, ga in gloss_aligns:
				
				gloss = gloss.lower()
				trans = trans.lower()
				
				gloss_tokens = gloss.split()
				trans_tokens = trans.split()
				
				alignments = Alignment()
				
				# For each line in the alignment...
				for ga_line in ga.split('\n'):
					
					# Skip empties...
					if not ga_line.strip() or len(ga_line.split()) != 5:
						continue
									
					gloss_i, trans_i, hash, gloss_w, trans_w = ga_line.split()
					
					# Also skip morpheme splits.
					if '.' in gloss_i:
						continue
					
					for trans_sub in trans_i.split(','):
						if int(trans_sub)-1 < 0:
							continue
						alignments.add((int(gloss_i), int(trans_sub)))
						
				sents.append(AlignedSent(gloss_tokens, trans_tokens, alignments))		
		return sents
	
			

				
				
			


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('c', metavar='CONF')
	
	args = p.parse_args()
	
	np = NAACLParser(args.c)
	
	np.get_corpus()
	