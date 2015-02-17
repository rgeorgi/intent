#!/usr/bin/env python

from xigt.codecs import xigtxml
import argparse
from corpora.IGTCorpus import IGTInstance
import sys
from igt.rgxigt import RGCorpus
from utils.argutils import existsfile, CommandLineException, writefile
import interfaces.mallet_maxent
import pickle

def xigt_process(xigt_corpus, classifier, posdict, out_xml):
	'''
	Process IGT and add alignment info.
	
	@param xigt_corpus:
	'''
	
	# Initialize a new corpus...
	new_corp = RGCorpus()
	
	# Load the POSDict if it's given
	if posdict:
		posdict = pickle.load(open(posdict, 'rb'))
	
	for inst in xigt_corpus.igts:
		# -- 1) Convert the IGT Instance from the default XIGT format
		#       to the internal subclass.
		igt = IGTInstance.fromXigt(inst)
		
		
		c = interfaces.mallet_maxent.MalletMaxent(classifier)
		pos_tokens = igt.lang_line_classifications(c, lowercase=True, posdict=posdict)
		
		# -- 3) Add this new instance to the output.
		new_corp.add(igt)
	
	# Now, dump it out.
	xigtxml.dump(out_xml, new_corp)
					


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-i', '--input', help='The input XIGT-XML document to parse.', type=existsfile, required=True)
	p.add_argument('-c', '--classifier', help='The input classifier for the POS tagging', type=existsfile, required=True)
	p.add_argument('-d', '--dict', help='The POS dict to help the classifier on the glosses.', type=existsfile)
	p.add_argument('-o', '--output', help='The output path to write the aligned output.', type=writefile, required=True)
	
	
	try:
		args = p.parse_args()
	except CommandLineException as cle:
		print(cle,end='\n\n')
		p.print_help()
		sys.exit(1)
	
	xigt_corpus = xigtxml.load(args.input)
	xigt_process(xigt_corpus, args.classifier, args.dict, args.output)