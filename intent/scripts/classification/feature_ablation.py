'''
Created on Oct 1, 2014

@author: rgeorgi
'''
# Global Imports ---------------------------------------------------------------
import glob, os, pickle
from collections import OrderedDict
from multiprocessing import Pool

# Internal imports -------------------------------------------------------------
from intent.interfaces.MalletMaxentTrainer import MalletMaxentTrainer
from intent.utils.ConfigFile import ConfigFile
from intent.ingestion.xaml.XamlParser import XamlParser
from intent.utils.argutils import ArgPasser


def produce_files(**c):
	
	# Set up the output files
	outdir = c.get('outdir')
	c['tag_out'] = os.path.join(outdir, 'ablation_tags.txt')
	c['class_out'] = os.path.join(outdir, 'ablation_class.txt')
	
	c['maxent_path'] = os.path.join(outdir, 'ablation-model.maxent')
	
	c['tag_f'] = open(c.get('tag_out'), 'w', encoding='utf-8')
	c['class_f'] = open(c.get('class_out'), 'w', encoding='utf-8')
	
	c = ArgPasser(c)
	
	xp = XamlParser(**c)
	
	xml_files = glob.glob(os.path.join(c.get('input_dir'), c.get('pattern', default='*.xml')))

	for x_f in xml_files:
		xp.parse(x_f, **c)
	return c

def test_results(**c):
	train, test = m.train_txt(c['class_out'], c['maxent_model'])
	return train, test
	
def test_feature(**c):
	c = produce_files(**c)
	c['class_f'].close()
	c['tag_f'].close()
	train, test = test_results(**c)
	return train, test
	
def ablation(**c):
	always_on = []
	other_feats = [ ('basicGrams','feat_basic'),
					('alignedTag','feat_align'),
					('gramHasNumber','feat_has_number'),
					('suffix','feat_suffix'),
					('prefix','feat_prefix'),
					('numGrams','feat_morph_num'),
					('prevGrams','feat_prev_gram'),
					('nextGrams','feat_next_gram'),
					('prevGramDict','feat_prev_gram_dict'),
					('nextGramDict','feat_next_gram_dict'),
					('dictTag','feat_dict')]
	combos = [('affixes', ['feat_suffix',
							'feat_prefix']),
			  ('context', ['feat_prev_gram',
						'feat_next_gram']),
			  ('dict_context', ['feat_prev_gram_dict', 
							'feat_next_gram_dict']),
			  ('all_dict', ['feat_prev_gram_dict', 
							'feat_next_gram_dict', 
							'feat_dict']),
			  ('best', ['feat_basic',
			  			'feat_prev_gram_dict',
						'feat_next_gram_dict',
						'feat_dict',
						'feat_suffix',
						'feat_prefix',
						'feat_next_gram',
						'feat_prev_gram',
						'feat_align'])
			  ]
	
	performance = OrderedDict()
	
	for feat in always_on:
		c[feat] = True
		
	for title, feat in other_feats:
		
		# RESET
		for other_title, other_feat in other_feats:
			c[other_feat] = False
			
		# Test that feature alone
		print("=============== TESTING %s" % feat)
		c[feat] = True
		train, test = test_feature(**c)
		performance[title] = (train, test)
		
	for name, featlist in combos:
		
		# RESET
		for other_title, other_feat in other_feats:
			c[other_feat] = False
			
		# Add combo features
		for feat in featlist:
			c[feat] = True
			
		train, test = test_feature(**c)
		performance[name] = (train, test)
		
	for feat in performance:
		print('%s,%s,%s' % (feat, performance[feat][0], performance[feat][1]))
		

if __name__ == '__main__':
	c = ConfigFile('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/conf/classification/feature_ablation.conf')

	if c.get('posdict'):
		c['posdict'] = pickle.load(open(c.get('posdict'), 'rb'))


	m = MalletMaxentTrainer()
	c['maxent_model'] = m
	
	ablation(**c)

	#c['feat_align'] = True
	#print(test_feature(**c))