'''
Created on Oct 14, 2013

@author: rgeorgi
'''

import os, sys, re
from optparse import OptionParser
from utils.commandline import require_opt
import ConfigParser
from trees.ptb import parse_ptb_string
from treebanks.common import process_tree, write_files, raw_writer,\
	traintest_split
from pos.TagMap import TagMap
import codecs
from utils.ConfigFile import ConfigFile
from utils.systematizing import notify
from treebanks.TextParser import TextParser
import nltk

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
		
		sent_count = 0
		for negra_string in negra_trees:
			negra_tree = nltk.Tree.parse(negra_string)
			sent_str, gold_str = process_tree(negra_tree, delimeter, maxlength, tm, simplify = True)
	
			if sent_str:
				all_sents.append(sent_str)
				gold_sents.append(gold_str)
				
				sent_count+=1			
				if sentence_limit and sent_count == sentence_limit:
					break
	
		write_files(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents)
		if trainraw:
			raw_train_sents, raw_test_sents = traintest_split(all_sents, split)
			raw_writer(trainraw, raw_train_sents)
			
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
	parser = OptionParser(version=program_version_string, epilog=program_longdesc, description=program_license)
	parser.add_option("-c", "--conf", dest="conf", help="set conf file [default: %default]", metavar="FILE")
		
	# set defaults
	parser.set_defaults()
	
	# process options
	(opts, args) = parser.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, "Please specify the configuration file with -c or --conf", True)
		
	if errors:
		raise Exception("There were errors found in processing.")
	
	# MAIN BODY #
	p = NegraParser(opts.conf)
	p.parse()