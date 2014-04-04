'''
Created on Apr 3, 2014

@author: rgeorgi
'''

import argparse
from alignment.Alignment import AlignedCorpus
import sys
from _collections import defaultdict
from utils.TwoLevelCountDict import TwoLevelCountDict

def analyze_giza(source, target, st, ts, output):
	# Read in the source/target alignment
	c_st = AlignedCorpus()
	c_st.read_giza(source, target, st)
	
	# Read in the target/source alignment
	c_ts = AlignedCorpus()
	c_ts.read_giza(target, source, ts)
		
	# Set up the counts for the alignments
	apairs = TwoLevelCountDict()
	
	# Now go through each set of alignments and count up what gets
	# aligned to what.
	for asent in c_st:
		for s_word, t_word in asent.wordpairs():
			apairs.add(s_word,t_word)
			
	# Go through for the target -- source alignment, reversing the order
	# of source and target in the wordpairs.
	for asent in c_ts:
		for t_word, s_word in asent.wordpairs():
			apairs.add(s_word,t_word)
			
	# Now, let's go through what GIZA picked up and see what the most frequent
	# alignments are.
	
	delimiter = '\xb0'
	
	for s_word in apairs.keys():
		output.write('%s%s' % (s_word, delimiter))
		
		total = apairs.total(s_word)
		output.write('%s%s' % (total, delimiter))

		counts = sorted(apairs[s_word].items(), key=lambda x: x[1], reverse=True)
		for t_word, count in counts:
			output.write(delimiter.join([t_word, str(count), str(count / total)]))
		output.write('\n')

			
def outputstream(arg):
	f = open(arg, 'w')
	return f

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('--ts', dest='ts', help='GIZA target-source alignment file', required=True)
	p.add_argument('--st', dest='st', help='GIZA source-target alignment file', required=True)
	p.add_argument('-s', dest='source', help='Source text file.', required=True)
	p.add_argument('-t', dest='target', help='Target text file', required=True)
	p.add_argument('-o', dest='output', help='Output', default=sys.stdout, type=outputstream)
	
	args = p.parse_args()
	
	analyze_giza(args.source, args.target, args.st, args.ts, args.output)