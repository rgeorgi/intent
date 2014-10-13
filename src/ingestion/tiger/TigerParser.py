'''
Created on Oct 23, 2013

@author: rgeorgi
'''
from treebanks.pml.pml import Alignments, TreeList
from optparse import OptionParser
import sys
from utils.commandline import require_opt
import os.path
from treebanks.common import raw_writer, write_files, traintest_split,\
	write_mallet
from pos.TagMap import TagMap
from utils.systematizing import notify
from utils.ConfigFile import ConfigFile

import re
from treebanks.TextParser import TextParser
from corpora.POSCorpus import POSToken, POSCorpus, POSCorpusInstance
import pickle
import chardet
from utils.encodingutils import getencoding
import codecs

class TigerParser(TextParser):
	
	def __init__(self, conf):
		self.conf = conf


	def parse(self):
		c = ConfigFile(self.conf)
		
		xml = c['xml']
		tagmap = c['tagmap']
		trainfile = c['trainfile']
		testfile = c['testfile']
		goldfile = c['goldfile']
		sentlimit = c['sentence_limit']
		delimeter = c['delimeter']
		split = int(c['trainsplit'])
		outdir = c['outdir']
		maxlength = c['maxlength']
		minlength = c['minlength']
		trainraw = c['trainraw']
		testraw = c['testraw']
		

		# Open the tiger xml file.
		
		
		xml_f = codecs.open(xml, 'r', encoding='iso-8859-1')
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
		
		corpus = POSCorpus()
		
		for sent in sents:
			
			inst = POSCorpusInstance()
			
			sent_str = ''
			gold_str = ''
			

# 			terms = s.findAll('t')
			terms = re.findall('<t.*?/>', sent)
						
			# Skip the current sentence if it's too long
			if (maxlength and len(terms) > maxlength) or (minlength and len(terms) < minlength):
				continue
			
			for term in terms:
				
				pos = re.search('pos="(.*?)" ', term).group(1)
				word = re.search('word="(.*?)" ', term).group(1)
				
				if tm:
					pos = tm[pos]
					
				token = POSToken(word, pos)
				inst.append(token)
				
				sent_str += '%s ' % word
				gold_str += '%s%s%s ' % (word, delimeter, pos)
				
			corpus.add(inst)
			
			gold_sents.append(gold_str.strip())
			all_sents.append(sent_str.strip())
	
			sent_idx += 1
			if sent_idx == sentlimit:
				break
		
		corpus.writesplit(trainfile, testfile, split, 'slashtags', outdir=outdir)
		corpus.writesplit(trainraw, testraw, split, 'raw', outdir=outdir)
		
# 		write_files(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents)
# 		write_mallet(outdir, split, testfile, trainfile, goldfile, all_sents, gold_sents, lowercase=True)
# 		train_raw_snts, test_raw_snts = traintest_split(all_sents, split)
# 		raw_writer(trainraw, train_raw_snts)

# 		notify()
		
		

if __name__ == '__main__':
	p = OptionParser()
	p.add_option('-c', '--conf', help='Configuration file')
	
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, 'You must specify a configuration file with -c or --conf', True)
	
	if errors:
		p.print_help()
		sys.exit()
	
	tp = TigerParser(opts.conf)
	tp.parse()
	
