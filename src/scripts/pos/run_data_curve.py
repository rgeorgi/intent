'''
This script is intended to run a set of POS experiments
by varying the amount of training data used to produce a curve.

@author: rgeorgi
'''
import argparse
from utils.argutils import configfile, existsfile, writedir
from corpora.POSCorpus import POSCorpus
import os
from interfaces.stanford_tagger import StanfordPOSTagger
from interfaces import stanford_tagger
from eval import pos_eval


def full_run(c):
	# The step of sentences by which to increment.
	step_increment = 50
	
	curve_dir = os.path.abspath(writedir(c['curve_dir']))
	train_path = c['train_path']
	test_path = c['test_path']
	
	train_corpus = POSCorpus.read_slashtags(train_path)
	test_corpus = POSCorpus.read_slashtags(test_path)
	
	# Let's go ahead and strip the tags from the test corpus.
	raw_test_name = 'test_data.txt'
	raw_test_path = os.path.join(curve_dir, raw_test_name)
	
	# Also, define where we will store the curve points.
	curve_points = 'curve_data.txt'
	curve_f = open(os.path.join(curve_dir, curve_points), 'w')
	
	test_corpus.write(raw_test_name, 'raw', outdir=curve_dir)
	
	# Now, let's add 100 sentences at a time until we max out.
	sent_limit = 0
	while sent_limit < len(train_corpus):
		
		# Adding 100 to the limit, starting from zero, means
		# we will get the last <99 instances too.
		actual_limit = sent_limit+step_increment
		sub_corpus = POSCorpus(train_corpus[0:actual_limit])

		# Let's create the necessary filenames.
		sub_train_path = os.path.join(curve_dir, '%d_train.txt' % actual_limit)
		sub_model_path = os.path.join(curve_dir, '%d_train.model' % actual_limit)
		sub_tag_path =   os.path.join(curve_dir, '%d_tagged.txt' % actual_limit)
		sub_result_path = os.path.join(curve_dir, '%d_result.txt' % actual_limit)
		
		
		# Now, let's write out the subset.
		sub_corpus.write(os.path.basename(sub_train_path), 'slashtags', outdir=curve_dir)
		
		# Next, train the parser.
		stanford_tagger.train(sub_train_path, sub_model_path)
		
		# Now, run it.
		stanford_tagger.test(raw_test_path, sub_model_path, sub_tag_path)
		
		# Load the result of the tagging...
		result_corpus = POSCorpus.read_slashtags(sub_tag_path)
		
		acc = pos_eval.poseval(result_corpus, test_corpus)
		curve_f.write('%d,%.2f\n' % (len(sub_corpus), acc))
		curve_f.flush()
		

		# Now, increase the sentence limit
		sent_limit += step_increment
		
	curve_f.close()
		
	

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-c', '--conf', type=configfile, required=True)
	
	args = p.parse_args()
	
	full_run(args.conf)