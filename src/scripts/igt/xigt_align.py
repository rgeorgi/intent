#!/usr/bin/env python

from xigt.codecs import xigtxml
import argparse
from corpora.IGTCorpus import IGTInstance, IGTCorpus
import sys
from igt.rgxigt import RGCorpus, rgencode
from utils.argutils import existsfile, CommandLineException, writefile

def xigt_process(xigt_corpus, out_xml):
	'''
	Process IGT and add alignment info.
	
	@param xigt_corpus:
	'''
	
	xigt_corpus.giza_align()
	xigtxml.dump(out_xml, xigt_corpus)
					


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
	
	xigt_corpus = RGCorpus.load(args.xml)
	
	xigt_process(xigt_corpus, args.out)