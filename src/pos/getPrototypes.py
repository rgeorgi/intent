'''
Created on Oct 22, 2013

@author: rgeorgi
'''
from optparse import OptionParser
import sys
from utils.commandline import require_opt
from utils.ConfigFile import ConfigFile
from utils.TwoLevelCountDict import TwoLevelCountDict
from utils.SetDict import SetDict
import re
from utils.encodingutils import getencoding
import codecs

def get_prototypes(tagged_path, proto_out, delimeter, 
				   ignoretags = [], unambiguous = False,
				   maxproto = 0):
	
	encoding = getencoding(tagged_path)	
	
	tagged_file = codecs.open(tagged_path, 'r', encoding=encoding)
	
	tag_word_dict = TwoLevelCountDict()
	word_tag_dict = TwoLevelCountDict()
	
	proto_dict = SetDict()
	
	for line in tagged_file:
		tokens = line.split()
		for token in tokens:
			word, pos = re.search('(^.*)%s(.*?)$' % delimeter, token).groups()
			if pos not in ignoretags:
				word = word.lower()
				tag_word_dict.add(pos, word)
				word_tag_dict.add(word, pos)
	
	numproto = 0
	# First, let's pick the maxproto most frequent words for a tag.
	for tag in tag_word_dict.keys():		
		words = tag_word_dict[tag].most_frequent(minimum=1, num = None)
		found_words = 0
		for word in words:
			
			freq_tag = word_tag_dict[word].most_frequent(minimum=1)
			
			
			if freq_tag and freq_tag[0] == tag:
# 			if freq_tag:
				
				proto_dict.add(freq_tag[0], word)
				numproto += 1
				found_words += 1
			
			if maxproto and found_words == maxproto:
				break
			
	print('%s Prototypes found.' % numproto)

			
	# Now, set up the proto file for writing.
	proto_file = open(proto_out, 'w')
	for tag in proto_dict:
		proto_file.write(tag)
		for word in proto_dict[tag]:
			proto_file.write('\t'+word.lower()) # LOWERCASE for testing
		proto_file.write('\n')
	proto_file.close()
			

if __name__ == '__main__':
	p = OptionParser()
	p.add_option('-c', '--conf', help='Configuration file')
	
	opts, args = p.parse_args(sys.argv)
	
	errors = require_opt(opts.conf, 'Missing conf file', True)
	
	if errors:
		p.print_help()
		sys.exit()
		
	c = ConfigFile(opts.conf)
	get_prototypes(c['taggedfile'], 
					c['protofile'], 
					c['delimeter'], 
					c['ignoretags'],
					c['unambiguous'],
					c['maxproto'])
	
	