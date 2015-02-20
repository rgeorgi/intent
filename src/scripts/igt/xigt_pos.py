#!/usr/bin/env python

from xigt.codecs import xigtxml
import argparse
from corpora.IGTCorpus import IGTInstance
import sys
from utils.argutils import existsfile, CommandLineException, writefile
import interfaces.mallet_maxent
import pickle
from utils.setup_env import c

def xigt_process(xigt_corpus, out_xml):
	'''
	Process IGT and add alignment info.
	
	@param xigt_corpus:
	'''
	
	# Load the POSDict from the env.conf settings...
	if c.get('pos_dict'):
		posdict = pickle.load(open(c.get('pos_dict'), 'rb'))
	
	# Initialize the gloss line classifier
	c = interfaces.mallet_maxent.MalletMaxent(c['classifier_model'])
	
	for igt in xigt_corpus.igts:
		
		pos_tokens = igt.lang_line_classifications(c, lowercase=True, posdict=posdict)
		
		# -- 3) Add this new instance to the output.
		new_corp.add(igt)
	
	# Now, dump it out.
	xigtxml.dump(out_xml, new_corp)
					


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-i', '--input', help='The input XIGT-XML document to parse.', type=existsfile, required=True)
	p.add_argument('-o', '--output', help='The output path to write the aligned output.', type=writefile, required=True)
	
	
	try:
		args = p.parse_args()
	except CommandLineException as cle:
		print(cle,end='\n\n')
		p.print_help()
		sys.exit(1)
	
	xigt_corpus = xigtxml.load(args.input)
	xigt_process(xigt_corpus, args.output)