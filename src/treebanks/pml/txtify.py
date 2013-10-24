'''
Created on Oct 23, 2013

@author: rgeorgi
'''
from treebanks.pml.pml import Alignments, TreeList
from ConfigParser import ConfigParser
from optparse import OptionParser
import sys
from utils.commandline import require_opt
import os.path
from treebanks.common import raw_writer, write_files
from pos.TagMap import TagMap
from utils.systematizing import notify

def parse_pml(align, outdir, split, trainfile, testfile, goldfile, projtrain, projtest, projgold, delimeter, eng_tagmap, hin_tagmap):
	a = Alignments(align)
	engpath = os.path.join(os.path.dirname(align), a.a)
	hinpath = os.path.join(os.path.dirname(align), a.b)	
	
	engtrees = TreeList(engpath)
	hintrees = TreeList(hinpath)
	
	eng_snts = []
	hin_snts = []
	
	eng_raw_snts = []
	hin_raw_snts = []
	
	proj_snts = []

	eng_tm = None
	hin_tm = None
	if eng_tagmap:
		eng_tm = TagMap(eng_tagmap)
	if hin_tagmap:
		hin_tm = TagMap(hin_tagmap)
	
	
	for alignment in a.sents:
		engtree = engtrees.find_id(alignment.a)
		hintree = hintrees.find_id(alignment.b)
		

		
		# Remap the hindi tags when a tagmap is provided:
		if hin_tm:
			for b_node in hintree.nodes():				
				b_node.pos = hin_tm[b_node.pos]
				
		eng_raw_snts.append(engtree.to_snt(clean=True))
		hin_raw_snts.append(hintree.to_snt(clean=True))
		
		# Let's start by prepping both the sentences for this...
		eng_snts.append(engtree.to_pos(delimeter = delimeter, clean = True))
		hin_snts.append(hintree.to_pos(delimeter = delimeter, clean = True))
		
		# Now, let's projected the POS tags
		for b_node in hintree.nodes():			
			aligned_pairs = filter(lambda pair: pair.b == b_node.id, alignment.pairs)
			projected = False
			for aligned_pair in aligned_pairs:
				a_node = engtree.find_id(aligned_pair.a)
				if a_node:
					
					# Do the remapping of the projected POS
					a_tag = a_node.pos
					
					# Only procede if a valid tag was found...
					if a_tag:

						if eng_tm:							
							a_tag = eng_tm[a_tag]
							
						# Project the projected POS				
						b_node.pos = a_tag
						projected = True
			
			if not projected:
				b_node.pos = 'UNK'
					
			
		# Now, get the sentence with the projected tags...
		proj_snts.append(hintree.to_pos(delimeter = delimeter, clean = True))
		
	write_files(outdir, split, testfile, trainfile, goldfile, hin_raw_snts, hin_snts)
	write_files(outdir, split, projtest, projtrain, projgold, hin_raw_snts, proj_snts)
	notify()
		
		

if __name__ == '__main__':
	p = OptionParser()
	p.add_option('-c', '--conf', help='Configuration file')
	
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, 'You must specify a configuration file with -c or --conf', True)
	
	if errors:
		p.print_help()
		sys.exit()
	
	c = ConfigParser(defaults={'eng_tagmap':None, 'hin_tagmap':None})
	c.read(opts.conf)
	parse_pml(c.get('pml', 'align'),
			  c.get('pml', 'outdir'),
			  c.get('pml', 'trainsplit'),
			  c.get('pml', 'trainfile'),
			  c.get('pml', 'testfile'),
			  c.get('pml', 'goldfile'),
			  c.get('pml', 'projtrain'),
			  c.get('pml', 'projtest'),
			  c.get('pml', 'projgold'),
			  c.get('pml', 'delimeter'),
			  c.get('pml', 'eng_tagmap'),
			  c.get('pml', 'hin_tagmap'))