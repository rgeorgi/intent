'''
Created on Mar 17, 2014

@author: rgeorgi
'''

from treebanks.xigt.XigtParser import XigtParser 
import argparse
from utils.ConfigFile import ConfigFile
import pickle
from igt.igtutils import clean_lang_string, clean_trans_string,\
	clean_gloss_string
from corpora.IGTCorpus import IGTInstance, IGTTier, IGTAlignmentException
import os
from interfaces import stanford_tagger
from nltk.tag.util import str2tuple
from utils.Token import morpheme_tokenizer, tokenize_string
from alignment.Alignment import AlignedSent

#===============================================================================
# XIGT Processing
#===============================================================================

def process_xigt(**kwargs):
	
	xigt_path = kwargs.get('xigt_file')
	outdir = kwargs.get('outdir')
	prefix = kwargs.get('prefix')
	
	proj_path = kwargs.get('proj_file')
	
	os.makedirs(outdir, exist_ok=True)
	
	if proj_path:
		proj_file = open(os.path.join(outdir, proj_path), 'w')
	
	pos_model = kwargs.get('pos_model')
	
	pkl = False
	
	if not pkl:
		xp = XigtParser()
		xp.parse_file(xigt_path)
		corpus = xp.corpus
		pickle.dump(corpus, open('spa.pkl', 'wb'))
	else:
		corpus = pickle.load(open('spa.pkl', 'rb')) 
	
	#===========================================================================
	# Open up the files
	#===========================================================================
	
	os.makedirs(outdir, exist_ok=True)
	
	gloss_path = '%sgloss.txt'%prefix
	trans_path = '%strans.txt'%prefix
	
	rawgloss_path = '%sgloss_raw.txt'%prefix
	rawtrans_path = '%strans_raw.txt'%prefix
	
	ha_gloss = '%sha_gloss.txt'%prefix
	ha_trans = '%sha_trans.txt'%prefix
	
	ha_gloss_f = open(os.path.join(outdir, ha_gloss), 'w')
	ha_trans_f = open(os.path.join(outdir, ha_trans), 'w')
	
	gloss_f = open(os.path.join(outdir, gloss_path), 'w')
	trans_f = open(os.path.join(outdir, trans_path), 'w')
	
	raw_gloss_f = open(os.path.join(outdir, rawgloss_path), 'w')
	raw_trans_f = open(os.path.join(outdir, rawtrans_path), 'w')
	
	for i in corpus:
		
		#=======================================================================
		# Clean the instance
		#=======================================================================
		
		rawlang = i.lang.text()
		rawgloss = i.gloss.text()
		rawtrans = i.trans.text()
		
		lang = clean_lang_string(rawlang)
		gloss = clean_gloss_string(rawgloss)
		trans = clean_trans_string(rawtrans)
		
		#=======================================================================
		# Write these out, but only if they contain stuff...
		#=======================================================================
		if gloss.strip() and trans.strip():
			raw_gloss_f.write(rawgloss+'\n')
			raw_trans_f.write(rawtrans+'\n')
					
			if False:
				gloss = ' '.join([t.seq for t in tokenize_string(gloss, tokenizer=morpheme_tokenizer)])
# 				trans = ' '.join([t.seq for t in tokenize_string(trans, tokenizer=morpheme_tokenizer)])
			gloss_f.write(gloss+'\n')
			trans_f.write(trans+'\n')
			
			gloss_f.flush()
			trans_f.flush()
		#=======================================================================
		# Make a new instance
		#=======================================================================
		
		newinst = IGTInstance(id=i.id)
		newlang = IGTTier.fromString(lang, kind='lang')
		newgloss = IGTTier.fromString(gloss, kind='gloss')
		newtrans = IGTTier.fromString(trans, kind='trans')
		
		newinst.extend([newlang, newgloss, newtrans])
		
		try:
			lha = newinst.lang_heuristic_alignment()
			trans_tags = stanford_tagger.tag([s.seq for s in newinst.trans], pos_model)
			tags = ([str2tuple(t[1])[1] for t in trans_tags])
			
			tagged_lang = AlignedSent(newlang, tags, lha.aln)
			
			langtagged = []
			
			for i, word in enumerate(tagged_lang.src):
				tags = tagged_lang.src_to_tgt_words(i+1)
				if not tags:
					tag = 'UNK'
				else:
					tag = tags[0]
					
				langtagged.append('%s/%s' % (word.seq, tag))
				
			proj_file.write(' '.join(langtagged)+'\n')
			proj_file.flush()
				
			
		except IGTAlignmentException as e:
			print(e)
		except UnicodeEncodeError as e:
			print(e)
		
		#=======================================================================
		# Get the gloss/translation alignment
		#=======================================================================
		
		aln = newinst.gloss_heuristic_alignment(grams_on=True)
		for source_token, target_token in aln.wordpairs():
			morph_str = ' '.join([m.seq for m in source_token.morphs(lowercase=True)])
			ha_gloss_f.write(morph_str+'\n')
			ha_trans_f.write(target_token.seq+'\n')
			
		
#===============================================================================
# MAIN FUNC
#===============================================================================

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('conf', help='Configuration File')
	
	args = p.parse_args()
	
	c = ConfigFile(args.conf)
	
	process_xigt(**c)
		