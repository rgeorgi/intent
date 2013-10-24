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

def get_prototypes(tagged_path, proto_out, delimeter, ignoretags = []):
	tagged_file = file(tagged_path, 'r')
	
	tag_word_dict = TwoLevelCountDict()
	word_tag_dict = TwoLevelCountDict()
	
	proto_dict = SetDict()
	
	for line in tagged_file:
		tokens = line.split()
		for token in tokens:
			word, pos = token.split(delimeter)
			if pos not in ignoretags:
				tag_word_dict.add(pos, word)
				word_tag_dict.add(word, pos)
			
	# For every word, let's pick its most frequently 
	for word in word_tag_dict.keys():
		freq = word_tag_dict[word].most_frequent(minimum=2)
		if freq:
			proto_dict.add(freq, word)
			
	# Now, set up the proto file for writing.
	proto_file = file(proto_out, 'w')
	for tag in proto_dict:
		proto_file.write(tag)
		for word in proto_dict[tag]:
			proto_file.write('\t'+word)
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
	get_prototypes(c['taggedfile'], c['protofile'], c['delimeter'], c['ignoretags'])
	
	