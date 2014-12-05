'''
Created on Nov 13, 2014

@author: rgeorgi
'''
from corpora.POSCorpus import POSCorpus
from utils.TwoLevelCountDict import TwoLevelCountDict
from collections import defaultdict
import sys
from tagging.features import SequenceFeature
from argparse import ArgumentParser
from utils.argutils import existsfile
from utils.ConfigFile import ConfigFile
from functools import reduce

	
#===============================================================================
# Produce the constraints file
#===============================================================================

def produce_constraints(in_path, out_path, min_count = 3): 
	
	p = POSCorpus.read_slashtags(in_path)
	
	print(in_path)	
		
	# Let's start a dictionary that's going to gather our features.
	feats = defaultdict(lambda: TwoLevelCountDict())
	
	alltags = set([])
	#alltags.add('O')
	alltags.add('X')

	
	for inst in p:
		
		sf = SequenceFeature(inst)
		while sf:
			
			alltags.add(sf.label)
			
			feats['word'].add(sf.form, sf.label)
			feats['prev'].add(sf.prev().form, sf.label)
			feats['next'].add(sf.next().form, sf.label)
			feats['pre-3'].add(sf.prefix(3), sf.label)
			feats['suf-3'].add(sf.suffix(3), sf.label)
			
			sf = sf.next()
			
		
			
	#===========================================================================
	# Now it's time to iterate through our statistics and make our constraints.
	#===========================================================================
	cf = open(out_path, 'w', encoding='utf-8')
	
	#===========================================================================
	# Let's try writing out the words we found with their labels, except
	# push all the probability mass to the first two most common tags.
	#===========================================================================
	
	words = feats['word']
	for word in words.keys():
		
		# Only write out if we've seen it at least X times.
		if words[word].total() >= min_count:
			
			# First write out the word
			cf.write(word)
			
			# Now, write out the distribution with all the probability shifted to the two most frequent tags.			
			best_items = sorted(words[word].items(), key=lambda x: x[1], reverse=True)[:2]
			
			best_counts = map(lambda x: x[1], best_items)
			best_total = reduce(lambda x,y: x+y, best_counts)
			
			best_dict = {tag:(count/best_total) for tag, count in best_items}
			
			for tag in alltags:
				if tag in best_dict:
					prob = best_dict[tag]
				else:
					prob = 0
					
				cf.write(' %s:%f' % (tag,prob))
			cf.write('\n')
				
				
			

			
	
# 	for feat in feats.keys():
# 		for val in feats[feat].keys():
# 			
# 			# Only write out features that have occurred an acceptable
# 			# number of times.
# 			count = feats[feat][val].total()
# 			if count >= min_count:
# 				
# 				# Now write out the probability across labels
# 				
# 				# 1) Begin with the feature name
# 				cf.write('%s-%s' % (feat, val))
# 				
# 				# 2) Now, give the distribution over all seen labels			
# 				for label, prob in feats[feat].distribution(val, use_keys=alltags, add_n=1):
# 					cf.write(' %s:%f' % (label, prob))
# 					
# 				
# 					
# 				cf.write('\n')
	cf.close()
	
if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--conf', type=existsfile, required=True)
	
	args = p.parse_args()

	c = ConfigFile(args.conf)
	
	produce_constraints(c['in_path'], c['out_path'], min_count = c['min_count'])
			
	