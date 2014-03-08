'''
Created on Feb 14, 2014

@author: rgeorgi
'''
from treebanks.TextParser import TextParser
from utils.ConfigFile import ConfigFile
import argparse
import re
import sys

from eval.align_eval import AlignEval

import pickle
import os

from alignment.Alignment import Alignment, AlignedSent, AlignedCorpus
from alignment.align import heuristic_align, heuristic_align_corpus
from corpora.POSCorpus import POSCorpus
from utils.encodingutils import getencoding
import codecs
from corpora.IGTCorpus import IGTCorpus, IGTInstance, IGTTier, IGTToken

class NAACLInstanceText(str):
	def __init__(self, seq=''):
		str.__init__(self, seq)
		
	def igt(self):		
		'''
		Create an IGTInstance out of the igt data. Note that this does not include
		the alignment or POS tags also included in the NAACL data, merely the raw instance.
		'''
		text = self.igttext()
		lines = text.split('\n')
		
		# Split the first line into attribute:value pairs.
		attrs = {sp[0].lower():int(sp[1]) for sp in [attr.split('=') for attr in lines[0].split()]}
		
		i = IGTInstance(id = attrs['igt_id'])
		
		for linenum in range(1, len(lines)):
			line = lines[linenum]
			if not line.strip():
				continue
			
			if linenum == 1:
				kind = 'lang'
			if linenum == 2:
				if len(lines) > 3:
					kind = 'gloss'
				elif len(lines) == 3:
					kind = 'trans'
			if linenum >= 3:
				kind = 'trans'
				
			tier = IGTTier(kind=kind)
			
			# Now, go through and add the tokens to the tier.
			words = line.split()
			for word_i in range(len(words)):
				word = words[word_i]
				token = IGTToken(seq=word, idx=word_i+1)
				tier.append(token)
				
			# Now add the tier to the instance
			i.append(tier)
			
		return i
				
	def glossalign(self):
		q5 = re.search('Q5:.*?\n([\S\s]+?)#+ Q5:', self).group(1)
		return get_align_indices(q5)
		
	
	def langalign(self):
		q4 = re.search('Q4:.*?\n([\S\s]+?)#+ Q4:', self).group(1)
		return get_align_indices(q4)
	
	
	def igttext(self):
		return re.search('(Igt_id[\s\S]+?)#+ Q1', self).group(1)

#===============================================================================
#  Helper functions
#===============================================================================

def get_align_indices(question):
	aligns = []
	for gloss_indices, trans_indices in re.findall('(\S+) (\S+) #', question):
		# Skip morphemes (for now)
		if '.' in gloss_indices:
			continue
		
		# Otherwise, deal with multiple alignments.
		for trans_i in trans_indices.split(','):
			aligns.append((int(gloss_indices), int(trans_i)))
	return aligns

#===============================================================================
#  Classes
#===============================================================================

class NAACLParser(TextParser):
	
	def __init__(self, conf):
		self.conf = ConfigFile(conf)
		
	def get_corpus(self):
		corpus = self.get_sents()
		alns = corpus.gloss_alignments()
		ha_alns = corpus.gloss_heuristic_alignments(lowercase=True, morph=True, stem=True)
				
		c = self.conf
		outdir = c['outdir']
		
		gloss_path = os.path.join(outdir, 'naacl_gloss.txt')
		trans_path = os.path.join(outdir, 'naacl_trans.txt')
		aln_path = os.path.join(outdir, 'naacl_aln.txt')
		ha_gloss = os.path.join(outdir, 'ha_gloss.txt')
		ha_trans = os.path.join(outdir, 'ha_trans.txt')
		
		
		ae = AlignEval(ha_alns, alns, debug=True)
		
		
		print(ae.all())		
		
		
		
	def get_sents(self):
		c = self.conf
		
		corpus = IGTCorpus()
		
		for root in c['roots'].split(','):
			
			encoding = getencoding(root.strip())			
			
			f = codecs.open(root.strip(), encoding=encoding)
			data = f.read()
			f.close()
		
			
			#===================================================================
			# Search for the gloss alignment and parse it.
			#===================================================================
			
			instances = re.findall('#+\nIgt_id[\s\S]+?Q6:', data)
			
			for instance in [NAACLInstanceText(i) for i in instances]:
				i = instance.igt()
				
				ga_indices = instance.glossalign()
				la_indices = instance.langalign()				
				
				for g_i, t_i in ga_indices:
					i.glossalign.add((g_i, t_i))
					
				for l_i, g_i in la_indices:
					i.langalign.add((l_i, t_i)) 
						
				# TODO: Zero-indexed makes me uncomfortable...
				corpus.append(i)
										
		return corpus
	
			

				
				
			


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('c', metavar='CONF')
	
	args = p.parse_args()
	
	np = NAACLParser(args.c)
	
	np.get_corpus()
	