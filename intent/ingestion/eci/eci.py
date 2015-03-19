'''
Created on Oct 2, 2014

@author: rgeorgi
'''
from utils.argutils import ArgPasser, existsfile, existsdir
from utils.fileutils import matching_files
import bz2
import os
import sys
import re
import utils.token
from corpora.POSCorpus import POSCorpus, POSCorpusInstance
from utils.token import POSToken

class ECITextParser(object):
	'''
	classdocs
	'''


	def __init__(self):
		'''
		Constructor
		'''
		
	def parse(self, **kwargs):
		kwargs = ArgPasser(kwargs)
		
		# Get the root of the corpus
		corpus_dir = kwargs.get('corpus_dir', t=existsdir)
		
		# Initialize a Corpus container
		corp = POSCorpus()
		
		# Next, get the file pattern.
		file_filter = kwargs.get('file_filter', '.*\.eci(?:\.bz2)?')
		
		# Now, get all the ECI files.		
		eci_paths = matching_files(corpus_dir, file_filter, recursive=True)
		
		for eci_path in eci_paths:
			
			# Open it as bz2 if it's compressed, otherwise
			# open it as a normal text file
			if os.path.splitext(eci_path)[1] == '.bz2':
				f = bz2.BZ2File(eci_path, 'rb')
			else:
				f = open(eci_path, 'rb')
			
			# Read the deata from the file...
			data = f.read().decode('latin-1')
			f.close()
			
			# Identify and iterate through all the sentences...
			sents = re.findall('<s.*?>([\S\s]+?)<\/s>', data)			
			for sent in sents:
				inst = POSCorpusInstance()
				
				tokens = utils.token.tokenize_string(sent.strip(), tokenizer=utils.token.whitespace_tokenizer)
				for token in tokens:
					t = POSToken.fromToken(token)
					inst.append(t)
				corp.append(inst)
				
		# Now, return the types/tokens
		print(len(corp.tokens()))
		print(len(corp.types()))		