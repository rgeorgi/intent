#!/usr/bin/env python

'''
Created on Apr 30, 2014

@author: rgeorgi
'''
from corpora.IGTCorpus import IGTCorpus
from interfaces.mallet_maxent import MalletMaxent
import pickle

c = IGTCorpus.from_text('/Users/rgeorgi/Dropbox/code/eclipse/aggregation/data/odin/train/deu.txt',
					merge=False)
classifier = MalletMaxent('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/models/gloss_classifier.maxent')

tagger_out = open('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/glosses/deu-classified_tagger.txt', 'w', encoding='utf-8') 
posdict = pickle.load(open('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/models/posdict.pickle', 'rb'))


for inst in c:
	
	sequence = inst.lang_line_classifications(classifier, posdict=posdict, 
											feat_dict=True,
											feat_next_gram=True,
											feat_prev_gram=True,
											feat_prefix=True,
											feat_suffix=True)
	
	# Now, for all of our tokens, let's do some data gathering.
	
	for token in sequence:
		tagger_out.write('%s/%s ' % (token.seq, token.label))
	
tagger_out.close()