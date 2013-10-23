'''
Created on Oct 14, 2013

@author: rgeorgi
'''

import os, sys, re
from optparse import OptionParser
from utils.commandline import require_opt
import ConfigParser
from trees.ptb import parse_ptb_string
from treebanks.common import process_tree, write_files
from pos.TagMap import TagMap
import codecs


def parse_negra(root, outdir, testfile, trainfile, goldfile, split = 90, maxlength = 10,
			delimeter='##', tagmap = None, remappedfile = None,
			start_section = 0, sentence_limit = 0):
	
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
		negra_tree = parse_ptb_string(negra_string)
		sent_str, gold_str = process_tree(negra_tree, delimeter, maxlength, tm)

		if sent_str:
			all_sents.append(sent_str)
			gold_sents.append(gold_str)
			
			sent_count+=1			
			if sentence_limit and sent_count == sentence_limit:
				break

	write_files(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents)


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
	c = ConfigParser.ConfigParser(defaults={'tagmap':None, 'remappedfile':None, 'start_section':'2','sentence_limit':'2000'})
	c.read(opts.conf)
	parse_negra(c.get('negra', 'root'), c.get('negra', 'outdir'), c.get('negra', 'testfile'), 
			c.get('negra', 'trainfile'), c.get('negra', 'goldfile'), c.getint('negra', 'trainsplit'), 
			c.getint('negra', 'maxlength'), c.get('negra', 'delimeter'),
			c.get('negra', 'tagmap'), c.get('negra', 'remappedfile'),
			c.getint('negra', 'start_section'),
			c.getint('negra', 'sentence_limit'))