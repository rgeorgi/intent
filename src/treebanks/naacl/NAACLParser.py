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
		
		print ae.all()
		print ae2.all()
		
				
		
	def get_sents(self):
		c = self.conf
		
		sents = AlignedCorpus()
		
		for root in c['roots'].split(','):
			f = open(root.strip())
			data = f.read()
			f.close()
			
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
	
			
	def extract_alignments(self):
		c = self.conf
		
		alnsents = []
		heur_sents = []
		heur_stem_sents = []
		extra_sents = []
		
		for root in c['roots'].split(','):
			f = open(root.strip())
			data = f.read()
			f.close()
			
			gloss_aligns = re.findall('Q5:[^\n]+\n(.+?)\n(.+?)\n[\s\n]+([0-9][\s\S]+?)######## Q5', data)
			
			stemmer = EnglishStemmer()

			#------------------------------------------------------------------------------
			# Lets go through the gloss_trans alignments
			
			for gloss, trans, ga in gloss_aligns:
				
				
				# Do some cleaning.
				gloss = gloss.lower()
				trans = trans.lower()
				
				gloss = re.sub('["\'\(]', '', gloss)
				trans = re.sub('["\'\(]', '', trans)
				
				gloss_tokens = gloss.split()
				trans_tokens = trans.split()
				
				print gloss
				print trans
								
				
				aln = ''
				heur_aln = ''
				heur_stem_aln = ''
				
				trans_stemmed_tokens = []
				for token in trans_tokens:
					try:
						stemmed_token = stemmer.stem(token)
					except UnicodeDecodeError as ude:
						stemmed_token = token
					trans_stemmed_tokens.append(token)
								
				
				for g in range(len(gloss_tokens)):
					gloss_token = gloss_tokens[g]		
					
					try:
						stemmed_token = stemmer.stem(gloss_token)
					except UnicodeDecodeError as ude:
						stemmed_token = gloss_token
								
					if gloss_token in trans_tokens:
						trans_index = trans_tokens.index(gloss_token)
						new_aln = '%d-%d ' % (g, trans_index)
						heur_aln += new_aln
						heur_stem_aln += new_aln
						
						# Add this matched word as an extra 1-1 sentence
						extra_sent = AlignedSent([gloss_token],[trans_tokens[trans_index]],[(0,0)])
						extra_sents.append(extra_sent)
						
					elif stemmed_token in trans_tokens:
						trans_index = trans_tokens.index(stemmed_token)
						heur_stem_aln += '%d-%d ' % (g, trans_index)
						
						extra_sent = AlignedSent([gloss_token],[trans_tokens[trans_index]],[(0,0)])
						extra_sents.append(extra_sent)
						
						
				
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
						aln += '%d-%d ' % (int(gloss_i)-1, int(trans_sub)-1)
						
	
				alnsent = AlignedSent(words=gloss_tokens, mots=trans_tokens, alignment=aln.strip())
				alnsents.append(alnsent)
				
				heursent = AlignedSent(words=gloss_tokens, mots=trans_tokens, alignment=heur_aln.strip())
				heur_sents.append(heursent)
				
				heur_stem_sent = AlignedSent(words=gloss_tokens, mots=trans_tokens, alignment=heur_stem_aln.strip())
				heur_stem_sents.append(heur_stem_sent)
				
		
		
		aln_file_a = 'ibm1.pickle'
		if not os.path.exists(aln_file_a):
			print 'pickling!'
			ibm = IBMModel1(alnsents)			
# 			pickle.dump(ibm, open(aln_file_a, 'w'))
			model_aligns = ibm.aligned()
			pickle.dump(model_aligns, open(aln_file_a, 'w'))
		else:
			print 'Unpickling!'
# 			ibm = pickle.load(open(aln_file_a, 'r'))
			model_aligns = pickle.load(open(aln_file_a, 'r'))
# 		model_aligns = ibm.aligned()
		
		
		
		
		
		aln_file_b = 'ibm2.pickle'
		if not os.path.exists(aln_file_b):
			ibm_extra = IBMModel1(alnsents+extra_sents)
			model_extra_aligns = ibm_extra.aligned()
# 			pickle.dump(ibm_extra, open(aln_file_b, 'w'))
			pickle.dump(model_extra_aligns, open(aln_file_b, 'w'))
		else:
# 			ibm_extra = pickle.load(open(aln_file_b, 'r'))
			model_extra_aligns = pickle.load(open(aln_file_b, 'r'))
			
# 		model_extra_aligns = ibm_extra.aligned()
		
		more_data = align.align_files('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/glosses/gloss.txt',
								   '/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/glosses/trans.txt')
# 		
# 		ibm_super = IBMModel1(alnsents+more_data[:500]+extra_sents)
# 		super_aligns = ibm_super.aligned()
		
		print AlignEval(zip(model_aligns, alnsents)).all()
		print AlignEval(zip(heur_sents, alnsents)).all()
		print AlignEval(zip(heur_stem_sents, alnsents)).all()
		print AlignEval(zip(model_extra_aligns, alnsents)).all()
# 		print AlignEval(zip(super_aligns[:539], alnsents)).all()
		print len(model_aligns)
		
		
		
		
# 		for test_aln, gold_aln in zip(model_aligns, alnsents):
# 			print test_aln.alignment
# 			print gold_aln.alignment
# 			print test_aln.alignment_error_rate(gold_aln.alignment)
			
				
				
				
			


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('c', metavar='CONF')
	
	args = p.parse_args()
	
	np = NAACLParser(args.c)
	
	np.get_corpus()
	