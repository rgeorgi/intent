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
from treebanks.common import raw_writer, write_files, traintest_split
from pos.TagMap import TagMap
from utils.systematizing import notify
from utils.ConfigFile import ConfigFile
from BeautifulSoup import BeautifulSoup
import re

def parse_tiger(xml, tagmap, trainfile, testfile, goldfile, sentlimit, delimeter, split, outdir, maxlength, minlength, trainraw):
	
	# Open the tiger xml file.
	xml_f = file(xml, 'r')
	xml_data = xml_f.read()
	xml_f.close()
	
	tm = None
	if tagmap:
		tm = TagMap(tagmap)
	
	# Find all the sentence elements in the xml file.
	sents = re.findall('<s [\s\S]+?</s>', xml_data)
	sent_idx = 0
	
	# Set up the lists that will keep the gathered data
	all_sents = []
	gold_sents = []
	
	for sent in sents:
		
		sent_str = ''
		gold_str = ''
		
		s = BeautifulSoup(sent)
		terms = s.findAll('t')
		
		# Skip the current sentence if it's too long
		if (maxlength and len(terms) > maxlength) or (minlength and len(terms) < minlength):
			continue
		
		
		for term in terms:
			pos = term['pos']
			word = term['word']
			
			if tm:
				pos = tm[pos]
			
			sent_str += '%s ' % word
			gold_str += '%s%s%s ' % (word, delimeter, pos)
			
		gold_sents.append(gold_str.strip())
		all_sents.append(sent_str.strip())

		sent_idx += 1
		if sent_idx == sentlimit:
			break
		
	write_files(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents)
	train_raw_snts, test_raw_snts = traintest_split(all_sents, split)
	raw_writer(trainraw, train_raw_snts)
# 	x = BeautifulSoup(xml_data)
	notify()
		
		

if __name__ == '__main__':
	p = OptionParser()
	p.add_option('-c', '--conf', help='Configuration file')
	
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, 'You must specify a configuration file with -c or --conf', True)
	
	if errors:
		p.print_help()
		sys.exit()
	
	c = ConfigFile(opts.conf)
	
	parse_tiger(c['xml'], c['tagmap'], c['trainfile'], c['testfile'], 
				c['goldfile'], c['sentence_limit'], c['delimeter'], 
				c['trainsplit'], c['outdir'], c['maxlength'], 
				c['minlength'], c['trainraw'])