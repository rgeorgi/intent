'''
Created on Mar 6, 2014

@author: rgeorgi
'''

# Global imports ---------------------------------------------------------------
import argparse, sys

# Internal Imports -------------------------------------------------------------
from intent.utils.ConfigFile import ConfigFile
from intent.utils.TwoLevelCountDict import TwoLevelCountDict
from intent.utils.TagCounter import TagCounter


def get_constraints(tagged_path, out_path, lowercase = True, delimeter='/'):
	output = open(out_path, 'w') 
	
	tp = open(tagged_path, 'r')
	
	tc = TagCounter(tagged_path, format = 'mallet')
	for word in tc.keys():
		
		#=======================================================================
		#  Filter out singletons...
		#=======================================================================
		if False and tc.total(word) <= 1:
			continue
		
		
		# Write out the "word" feature
		output.write(word)
		
	
		
		# Now write out the distribution over the tags for the constraints.
		dist = tc.distribution(word)		
		for tag, prob in dist:
			prob = float(prob)
# 			probstr = '%.9f,%.9f' % (prob-0.3, min(1.0,prob+0.3))
			probstr = str(prob)			
# 			if tag == tc.most_frequent(word):
# 				probstr = '1.0'
# 			else:
# 				probstr = '0.0'
					
			output.write(' '+tag+':'+probstr)
			
		# Newline for next feature/word
		output.write('\n')
		
	output.close()
		

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('conf')
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	get_constraints(c['tagged_path'], c['out_path'])