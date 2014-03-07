'''
Created on Oct 23, 2013

@author: rgeorgi
'''
from treebanks.pml.pml import Alignments, TreeList
from argparse import ArgumentParser
import sys
from utils.commandline import require_opt
import os.path
from treebanks.common import raw_writer, write_files, write_mallet
from pos.TagMap import TagMap
from utils.systematizing import notify
from treebanks.TextParser import TextParser
from utils.ConfigFile import ConfigFile
from corpora.POSCorpus import POSCorpus, POSCorpusInstance

class PMLParser(TextParser):
	
	def __init__(self, conf):
		self.conf = conf
		
	def parse(self):
		c = ConfigFile(self.conf)
		align = c['align']
		outdir = c['outdir']
		split = c['trainsplit']
		trainfile = c['trainfile']
		testfile = c['testfile']
		goldfile = c['goldfile']
		projtrain = c['projtrain']
		projtest = c['projtest']
		projgold = c['projgold']
		delimeter = c['delimeter']
		rawfile = c['rawfile']
		a_tagmap = c['a_tagmap']
		b_tagmap = c['b_tagmap']
		
		a = Alignments(align)
		a_path = os.path.join(os.path.dirname(align), a.a)
		b_path = os.path.join(os.path.dirname(align), a.b)	
		
		a_trees = TreeList(a_path)
		b_trees = TreeList(b_path)
		
		a_snts = []
		b_snts = []
		
		a_raw_snts = []
		b_raw_snts = []
		
		b_proj_snts = []
	
		corpus = POSCorpus()
	
		a_tm = None
		b_tm = None
		if a_tagmap:
			a_tm = TagMap(a_tagmap)
		if b_tagmap:
			b_tm = TagMap(b_tagmap)
		
		#=======================================================================
		#  Start iterating through the sentences (each alignment is a sentence pair)
		#=======================================================================
		
		a_orig_corp = POSCorpus()
		a_proj_corp = POSCorpus()
		
		b_orig_corp = POSCorpus()
		b_proj_corp = POSCorpus()
		
		for alignment in a.sents:
			a_t = a_trees.find_id(alignment.a)
			b_t = b_trees.find_id(alignment.b)
			
			# Remap the foreign-language tags when a tagmap is provided:
			if b_tm:
				for b_node in b_t.nodes():				
					b_node.pos = b_tm[b_node.pos]
					
			a_c_i = a_t.to_pos_corpus_instance()
			b_c_i = b_t.to_pos_corpus_instance()
			
			a_orig_corp.add(a_c_i)
			b_orig_corp.add(b_c_i)
					
			a_raw_snts.append(a_c_i.raw())
			b_raw_snts.append(b_c_i.raw())
			
			# Let's start by prepping both the sentences for this...
			a_snts.append(a_c_i.slashtags(delimeter=delimeter))
			b_snts.append(b_c_i.slashtags(delimeter=delimeter))
			
			# Now, let's project the POS tags
			for b_node in b_t.nodes():
				
# 				aligned_pairs = filter(lambda pair: pair.b == b_node.id, alignment.pairs)
				aligned_pairs = [pair for pair in alignment.pairs if pair.b == b_node.id]
				
				projected = False
				for aligned_pair in aligned_pairs:
					a_node = a_t.find_id(aligned_pair.a)
					if a_node is not None:
						
						# Do the remapping of the projected POS
						a_tag = a_node.pos
						
						# Only procede if a valid tag was found...
						if a_tag != None:
	
							if a_tm:							
								a_tag = a_tm[a_tag]
								
							# Project the projected POS				
							b_node.pos = a_tag
							projected = True
				
				if not projected:
# 					sys.stderr.write('%s, %s\n' % (b_node.id, b_node))
# 					sys.stderr.write(str(a_tag)+'\n')
					b_node.pos = 'UNK'
# 					sys.exit()
						
			# Now, get the sentence with the projected tags...
			b_proj_snts.append(b_t.to_pos(delimeter = delimeter, clean = True))
			
			b_proj_corp.add(b_t.to_pos_corpus_instance())
			
		b_proj_corp.writesplit(projtrain, projtest, split, 'slashtags', outdir=outdir, lowercase=True)
		b_orig_corp.writesplit(trainfile, testfile, split, 'slashtags', outdir=outdir, lowercase=True)
		b_orig_corp.writesplit(rawfile, testfile, 100, 'raw', outdir=outdir)
		
# 		write_mallet(outdir, split, testfile, trainfile, goldfile, b_raw_snts, b_snts, lowercase = True)
# 		write_mallet(outdir, split, projtest, projtrain, projgold, b_raw_snts, b_proj_snts, lowercase = True)
# 		raw_writer(os.path.join(outdir, rawfile), b_raw_snts)
		notify()
		
		

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('conf', help='Configuration file')
	
	args = p.parse_args()
	
	errors = require_opt(args.conf, 'You must specify a configuration file with -c or --conf', True)
	
	if errors:
		p.print_help()
		sys.exit()
	
	p = PMLParser(args.conf)
	p.parse()
