'''
Created on Jun 12, 2014

@author: rgeorgi
'''

# Built-in imports -------------------------------------------------------------
import argparse, pickle, sys, shelve
from collections import defaultdict
from functools import partial

# Internal imports -------------------------------------------------------------
from intent.utils.argutils import existsfile, existsdir
from intent.corpora.POSCorpus import POSCorpus
from intent.utils.dicts import TwoLevelCountDict


class POSDictBuilder(POSCorpus):
	'''
	Class to build a dictionary of word/POS pair probabilities.
	'''
	
	def __init__(self, seq=[]):
		self.wordlabelcount = TwoLevelCountDict()
		POSCorpus.__init__(self, seq=seq)
	
	def token_handler(self, tokens):
		'''
		Overwrite the POSCorpus method. 
		
		:param tokens:
		:type tokens:
		'''
		POSCorpus.token_handler(self, tokens)
		for token in tokens:
			self.wordlabelcount[token.seq.lower()][token.label] += 1
		
	def pickle_dict(self, fp):		
		pickle.dump(self.wordlabelcount, open(fp, 'wb'))
		
		
		

def create_dictionary(**kwargs):
	pc = POSDictBuilder.read_slashtags(kwargs['corpus'])	
	pc.pickle_dict(kwargs['output'])

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-i', dest='corpus', help='POS Tagged Corpus', required=True, type=existsfile)
	p.add_argument('-o', dest='output', help='Destination for pickled POS dict', required=True)
	p.add_argument('--tagmap', help='Tag Map for tags', type=existsfile)
	
	args = p.parse_args()
	
	create_dictionary(**vars(args))