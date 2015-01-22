#!/usr/bin/env python

from xigt.codecs import xigtxml
import argparse
from corpora.IGTCorpus import IGTInstance
import sys
from igt.rgxigt import RGCorpus
from utils.argutils import existsfile, CommandLineException, writefile

def xigt_process(xigt_corpus, out_xml):
	'''
	Process IGT and add alignment info.
	
	@param xigt_corpus:
	'''
	
	# Initialize a new corpus...
	new_corp = RGCorpus()
	
	for inst in xigt_corpus.igts:
		# -- 1) Convert the IGT Instance from the default XIGT format
		#       to the internal subclass.
		igt = IGTInstance.fromXigt(inst)
		
		# -- 2) Next, obtain the heuristic alignment.
		gha = igt.gloss_heuristic_alignment()
		
		# -- 3) Add this new instance to the output.
		new_corp.add(igt)
	
	# Now, dump it out.
	xigtxml.dump(out_xml, new_corp)
					


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('xml', help='The input XIGT-XML document to parse.', type=existsfile)
	p.add_argument('out', help='The output path to write the aligned output.', type=writefile)
	
	try:
		args = p.parse_args()
	except CommandLineException as cle:
		print(cle,end='\n\n')
		p.print_help()
		sys.exit(1)
	
	xigt_corpus = xigtxml.load(args.xml)
	xigt_process(xigt_corpus, args.out)