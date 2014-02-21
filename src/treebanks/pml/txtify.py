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


def parse_pml(align, outdir, split, trainfile, testfile, goldfile, projtrain, projtest, projgold, delimeter, rawfile, a_tagmap, b_tagmap):
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

	a_tm = None
	b_tm = None
	if a_tagmap:
		a_tm = TagMap(a_tagmap)
	if b_tagmap:
		b_tm = TagMap(b_tagmap)
	
	
	for alignment in a.sents:
		a_t = a_trees.find_id(alignment.a)
		b_t = b_trees.find_id(alignment.b)
		

		
		# Remap the foreign-language tags when a tagmap is provided:
		if b_tm:
			for b_node in b_t.nodes():				
				b_node.pos = b_tm[b_node.pos]
				
		a_raw_snts.append(a_t.to_snt(clean=True))
		b_raw_snts.append(b_t.to_snt(clean=True))
		
		# Let's start by prepping both the sentences for this...
		a_snts.append(a_t.to_pos(delimeter = delimeter, clean = True))
		b_snts.append(b_t.to_pos(delimeter = delimeter, clean = True))
		
		# Now, let's projected the POS tags
		for b_node in b_t.nodes():			
			aligned_pairs = filter(lambda pair: pair.b == b_node.id, alignment.pairs)
			projected = False
			for aligned_pair in aligned_pairs:
				a_node = a_t.find_id(aligned_pair.a)
				if a_node:
					
					# Do the remapping of the projected POS
					a_tag = a_node.pos
					
					# Only procede if a valid tag was found...
					if a_tag:

						if a_tm:							
							a_tag = a_tm[a_tag]
							
						# Project the projected POS				
						b_node.pos = a_tag
						projected = True
			
			if not projected:
				b_node.pos = 'UNK'
					
			
		# Now, get the sentence with the projected tags...
		b_proj_snts.append(b_t.to_pos(delimeter = delimeter, clean = True))
		
	write_files(outdir, split, testfile, trainfile, goldfile, b_raw_snts, b_snts)
	write_files(outdir, split, projtest, projtrain, projgold, b_raw_snts, b_proj_snts)
	raw_writer(os.path.join(outdir, rawfile), b_raw_snts)
	notify()
		
		

if __name__ == '__main__':
	p = OptionParser()
	p.add_option('-c', '--conf', help='Configuration file')
	
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, 'You must specify a configuration file with -c or --conf', True)
	
	if errors:
		p.print_help()
		sys.exit()
	
	c = ConfigParser(defaults={'a_tagmap':None, 'b_tagmap':None, 'rawfile':None})
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
			  c.get('pml', 'rawfile'),
			  c.get('pml', 'a_tagmap'),
			  c.get('pml', 'b_tagmap'))