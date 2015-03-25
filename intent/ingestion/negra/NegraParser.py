'''
Created on Oct 14, 2013

@author: rgeorgi
'''

import os, sys, re
from argparse import ArgumentParser

from pos.TagMap import TagMap
import codecs
from utils.ConfigFile import ConfigFile
from utils.systematizing import notify
from ingestion.TextParser import TextParser
import nltk
from corpora.POSCorpus import POSCorpus, POSCorpusInstance, POSToken

class NegraParser(TextParser):
	
	def __init__(self, conf):
		self.conf = conf
		
	def parse(self):
		c = ConfigFile(self.conf)
		c.set_defaults({'maxLength':10, 'sentence_limit':0})
		
		root = c['root']
		outdir = c['outdir']
		testfile = c['testfile']
		trainfile = c['trainfile']
		goldfile = c['goldfile']
		split = c['trainsplit']
		maxlength = c.getint('maxLength')
		delimeter = c['delimeter']
		tagmap = c['tagmap']
		sentence_limit = c.getint('sentence_limit')
		trainraw = c['trainraw']
		minlength = c.getint('minlength')
		testraw = c['testraw']
			
		
		tm = None
		if tagmap:
			tm = TagMap(path=tagmap)
		
		# Open up the negra treebank (in PTB format)
		negra_f = codecs.open(root, 'r', encoding='latin-1', errors='strict')
		negra_lines = negra_f.read()
		negra_f.close()
		
		# Now, find all the trees.
		negra_trees = re.findall('%% Sent [0-9]+([\s\S]+?)\n\n', negra_lines)
		negra_trees = map(lambda tree: re.sub('[\s]+', ' ', tree), negra_trees)
		
		all_sents = []
		gold_sents = []
		
		corpus = POSCorpus()
		
		sent_count = 0
		for negra_string in negra_trees:
			
			# Start a corpus instance
			inst = POSCorpusInstance()
			
			
			negra_tree = nltk.Tree.parse(negra_string)
			
			if len(negra_tree) < minlength or len(negra_tree) > maxlength:
				continue
			
			for word, pos in negra_tree.pos():
				
				pos = re.sub(r'(.*?)-.*', r'\1', pos)
				if re.match('\*T', pos):
					continue

				if tagmap:
					pos = tm[pos]
				
				token = POSToken(word, pos)
				inst.append(token)
			if len(inst):
				corpus.add(inst)
				
				sent_count+=1			
				if sentence_limit and sent_count == sentence_limit:
					break
			
		print(outdir, trainfile)
		corpus.writesplit(trainfile, testfile, split, 'slashtags', delimeter=delimeter, lowercase=True, outdir=outdir)
		corpus.writesplit(trainraw, testraw, split, 'raw', outdir=outdir, lowercase=True)
		
# 		write_files(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents)
# 		if trainraw:
# 			raw_train_sents, raw_test_sents = traintest_split(all_sents, split)
# 			raw_writer(trainraw, raw_train_sents)
			
		notify()
	


if __name__ == '__main__':
	'''Command line options.'''
	
	program_name = os.path.basename(sys.argv[0])
	program_version = "v0.1"

	
	program_version_string = '%%prog %s' % (program_version)
	#program_usage = '''usage: spam two eggs''' # optional - will be autogenerated by optparse
	program_longdesc = '''''' # optional - give further explanation about what the program does
	program_license = "Copyright 2013 Ryan Georgi (Ryan Georgi)                                            \
				Licensed under the Apache License 2.0\nhttp://www.apache.org/licenses/LICENSE-2.0"


	# setup option parser
	parser = ArgumentParser(version=program_version_string, epilog=program_longdesc, description=program_license)
	parser.add_argument("-c", "--conf", dest="conf", help="set conf file [default: %default]", metavar="FILE", required=True)
		
	# set defaults
	parser.set_defaults()
	
	# process options
	opts = parser.parse_args()
	
	# MAIN BODY #
	p = NegraParser(opts.conf)
	p.parse()