'''
Created on Feb 14, 2014

@author: rgeorgi
'''
from treebanks.TextParser import TextParser
from utils.ConfigFile import ConfigFile
import argparse
import re
import sys

from eval.AlignEval import AlignEval
import os
from utils.encodingutils import getencoding
import codecs
from corpora.IGTCorpus import IGTCorpus, IGTInstance, IGTTier, IGTToken
import pickle
import nltk
from pos.TagMap import TagMap
from utils.Token import morpheme_tokenizer, tokenize_string
from interfaces.mallet_maxent import MalletMaxent
from alignment.Alignment import AlignedSent

class NAACLInstanceText(str):
	def __init__(self, seq=''):
		str.__init__(self, seq)
		
	def igt(self):		
		'''
		Create an IGTInstance out of the igt data. Note that this does not include
		the alignment or POS tags also included in the NAACL data, merely the raw instance.
		'''
		text = self.igttext()
		lines = text.split('\n')
		
		# Split the first line into attribute:value pairs.
		attrs = {sp[0].lower():int(sp[1]) for sp in [attr.split('=') for attr in lines[0].split()]}
		
		i = IGTInstance(id = attrs['igt_id'])
		
		for linenum in range(1, len(lines)):
			line = lines[linenum]
			if not line.strip():
				continue
			
			if linenum == 1:
				kind = 'lang'
			if linenum == 2:
				if len(lines) > 3:
					kind = 'gloss'
				elif len(lines) == 3:
					kind = 'trans'
			if linenum >= 3:
				kind = 'trans'
				
			tier = IGTTier(kind=kind)
			
			# Now, go through and add the tokens to the tier.
			words = line.split()
			for word_i in range(len(words)):
				word = words[word_i]
				token = IGTToken(seq=word, index=word_i+1)
				tier.append(token)
				
			# Now add the tier to the instance
			i.append(tier)
			
		return i
				
	def glossalign(self, debug=False):
		q5 = re.search('Q5:.*?\n([\S\s]+?)#+ Q5:', self).group(1)
		return get_align_indices(q5, debug=debug)
		
	
	def langalign(self):
		q4 = re.search('Q4:.*?\n([\S\s]+?)#+ Q4:', self).group(1)
		return get_align_indices(q4)
		
	def igttext(self):
		return re.search('(Igt_id[\s\S]+?)#+ Q1', self).group(1)

	def transtags(self, tagmap=None):
		q2 = re.search('Q2:.*?\n([\S\s]+)#+ Q2', self).group(1)
		treestring = q2.split('\n')[0]
		
		t = nltk.tree.Tree.parse(treestring)
		pos = t.pos()
		
		
		if tagmap:
			pos = [(w, tagmap.get(p)) for w, p in pos]
		
		return pos

				
	
#===============================================================================
#  Helper functions
#===============================================================================

def get_align_indices(question, debug=False):
	aligns = []
	
	leading_space = False
	
	for gloss_indices, trans_indices, words in re.findall('(\S+) (\S+) #(.*)', question):
		# Skip morphemes (for now)
		if '.' in gloss_indices:
			continue				
		
		# Otherwise, deal with multiple alignments.
		for trans_i in trans_indices.split(','):
			
			gloss_i = int(gloss_indices)
			trans_i = int(trans_i)
			
			# Although if for some stupid reason, if there is a leading space
			# in the sentence, it counts it. So let's mark that, not
			# count the leading space, and subtract 1 from the other indices.
			
			if not len(words.strip().split()) > 1:
				leading_space = True
				continue
				
			if leading_space:
				gloss_i -=1
				trans_i -=1
			
			if gloss_i >= 0 and trans_i >=0:			
				aligns.append((gloss_i, trans_i))
			
	return aligns

#===============================================================================
#  Classes
#===============================================================================

class NAACLParser(TextParser):
	
	def __init__(self):
		self._corpus = IGTCorpus()
		
		
	@property
	def corpus(self):
		if hasattr(self,'_corpus'):
			return self._corpus
		else:
			self.get_corpus()
			return self.corpus
				
	@property
	def alignments(self):
		return self.corpus.gloss_alignments()
		
	@property
	def heuristic_alignments(self):
		if hasattr(self, '_ha_alns'):
			return self._ha_alns
		else:
			self._ha_alns = self.corpus.gloss_heuristic_alignments()
			return self.heuristic_alignments
		

	def parse_files(self, filelist, **kwargs):				
		for root in filelist:
			self.parse_file(root, **kwargs)
			
	def parse_file(self, root, **kwargs):
		
		corpus = self.corpus
		
		encoding = getencoding(root.strip())			
		
		f = codecs.open(root.strip(), encoding=encoding)
		data = f.read()
		f.close()
	
		#c = MalletMaxent('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/all/xigt_grams.maxent')
		
		#===================================================================
		# Search for the gloss alignment and parse it.
		#===================================================================
		
		instances = re.findall('#+\nIgt_id[\s\S]+?Q6:', data)
		
		for instance in [NAACLInstanceText(i) for i in instances]:
			i = instance.igt()
			
			lang = os.path.basename(os.path.dirname(root))[:3]

			i.set_attr('file', root)
			i.set_attr('id', i._id)
			i.set_attr('lang', lang)	
						
			ga_indices = instance.glossalign(debug=i._id)
			la_indices = instance.langalign()				
			

			for g_i, t_i in ga_indices:
				i.glossalign.add((g_i, t_i))
				
	
				
			for l_i, g_i in la_indices:
				i.langalign.add((l_i, t_i)) 
					
			# TODO: Zero-indexed makes me uncomfortable...
			corpus.append(i)
			
			dump_feats = kwargs.get('dump_feats', None)
			if dump_feats is not None:
			
				tm = TagMap('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/prototypes/universal_mapping_eng.txt')
				tags = instance.transtags(tagmap=tm)
				#TODO: This is hardcoded...
				dump_feats[i.id] = tags
				
			tag_f = kwargs.get('tag_f', None)
			if tag_f is not None:
				tags = tag_f.get(i.id)
				if tags:					
					glosstags = AlignedSent(i.gloss, tags, i.glossalign)
					for token, tagpair in glosstags.wordpairs():
						word, tag = tagpair
						morphs = tokenize_string(token.seq, morpheme_tokenizer)
						feat_f = kwargs.get('feat_f')						
						if len(morphs) > 1:
							feat_f.write('%s ' % tag)
							for morph in morphs:
								morph_s = morph.seq.lower()
								feat_f.write('%s:1 ' % morph_s)
							feat_f.write('\n')
				
					
# 				dump_feats.write(' '.join(['%s/%s'%(t, w) for t, w in tags])+'\n')
# 				glosstags = AlignedSent(i.gloss, [t for w, t in tags], i.glossalign)
# 				print(glosstags.wordpairs())
# 				
# 				for word, tag in tags:
# 					
# 					morphs = tokenize_string(word, morpheme_tokenizer)
# 					if morphs:
# 						print('%s '%tag,end='')
# 						for morph in morphs:
# 							morph_s = morph.seq.lower()
# 							print('%s:1' % morph_s, end=' ')
# 						print()
					
				
	
	def write_files(self, gloss_f, trans_f, aln_f, ha_g_f, ha_t_f, morphs=False):
		#===========================================================================
		# Writing out the instances
		#===========================================================================
	
		for inst in self.corpus:
			gloss_tier = inst.gloss
			trans_tier = inst.trans
			aln = inst.gloss_alignments()
			
			#=======================================================================
			# For the alignment, we want to write the gloss index, the parent
			# word's index, and the target word to which both align.
			#=======================================================================
			
			if morphs:
				src_tokens = [g for g in gloss_tier.morphs(lowercase=True)]
			else:
				src_tokens = [g for g in gloss_tier]
			
			for g in range(len(src_tokens)):
				gloss_token = src_tokens[g]
				gloss_index = gloss_token.index
				
				tgt_indices = [str(aln[1]) for aln in aln.pairs(src=gloss_index)]
				aln_f.write('%s:%s:%s ' % (g+1,gloss_index, ','.join(tgt_indices)))
			
			
			gloss_f.write(' '.join([g.seq.lower() for g in src_tokens]) +'\n')
			trans_f.write(' '.join([t.seq.lower() for t in trans_tier]) + '\n')
			
			# Write newline
			aln_f.write('\n')
			
	
			
		for aln in ha_alns:
			for gloss, trans in aln.wordpairs():
				gloss_morphs = [m.seq for m in gloss.morphs(lowercase=True)]
				ha_g_f.write(' '.join(gloss_morphs)+'\n')
				ha_t_f.write(trans.text()+'\n')
				
				# Write out additional glosses:
# 				for g_m in gloss_morphs:
# 					ha_g_f.write(g_m+'\n')
# 					ha_t_f.write(trans.text()+'\n')
			

				
	#===========================================================================
	#  MAIN FUNCTION
	#===========================================================================
			


if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('c', metavar='CONF')
	
	args = p.parse_args()
	
	# Get the configuration file
	c = ConfigFile(args.c)
	
	#===========================================================================
	# Get the files to process and where to put the output. 
	#===========================================================================
	naacl_files = c['roots'].split(',')
	outdir = c['outdir']	
	

	#=======================================================================
	# Create the naacl parser and get the corpus.
	#=======================================================================
	pkl = False
	
	dump_path = os.path.join(outdir, 'tagged_words.pkl')
	feat_path = os.path.join(outdir, 'feats_morphs.txt')
	#dump_f = {}
	
	feat_f = open(feat_path, 'w')
	
	#mc = MalletMaxent()
	
	tag_f = pickle.load(open(dump_path, 'rb'))
				
	if not pkl:
		np = NAACLParser()
		np.parse_files(naacl_files, tag_f=tag_f, feat_f=feat_f)
		#pickle.dump(dump_f, open(dump_path, 'wb'))
	else:
		np = pickle.load(open('np.pkl', 'rb'))
		
	ha_alns = np.heuristic_alignments
	alns = np.alignments
	
	if not pkl:
		pickle.dump(np, open('np.pkl', 'wb'))

	#===========================================================================
	# Get the alignments for each language
	#===========================================================================
	
	ae = AlignEval(ha_alns, alns, debug=False)
	ger = AlignEval(ha_alns, alns, debug=False, filter=('lang', 'ger'))
	kkn = AlignEval(ha_alns, alns, debug=False, filter=('lang', 'kkn'))
	wls = AlignEval(ha_alns, alns, debug=False, filter=('lang', 'wls'))
	gli = AlignEval(ha_alns, alns, debug=False, filter=('lang', 'gli'))
	hua = AlignEval(ha_alns, alns, debug=False, filter=('lang', 'hua'))
	mex = AlignEval(ha_alns, alns, debug=False, filter=('lang', 'mex'))
	yaq = AlignEval(ha_alns, alns, debug=False, filter=('lang', 'yaq'))
	
	print('ALL ' + ae.all(), ae.instances)
	print('Ger ' + ger.all(), ger.instances)
	print('Kor ' + kkn.all(), kkn.instances)
	print('Wls ' + wls.all(), wls.instances)
	print('Gli ' + gli.all(), gli.instances)
	print('Hua ' + hua.all(), hua.instances)
	print('Mex ' + mex.all(), mex.instances)
	print('Yaq ' + yaq.all(), yaq.instances)
	
	#===========================================================================
	# Write out files
	#===========================================================================
	
	corp = np.corpus
	
	
# 	gloss_path = os.path.join(outdir, 'naacl_gloss.txt')
# 	trans_path = os.path.join(outdir, 'naacl_trans.txt')
# 	aln_path = os.path.join(outdir, 'naacl_aln.txt')
# 	ha_gloss = os.path.join(outdir, 'ha_gloss.txt')
# 	ha_trans = os.path.join(outdir, 'ha_trans.txt')
# 	
# 	# Create files...
# 	gloss_f = open(gloss_path, 'w')
# 	trans_f = open(trans_path, 'w')
# 	
# 	aln_f = open(aln_path, 'w')
# 	
# 	ha_g_f = open(ha_gloss, 'w')
# 	ha_t_f = open(ha_trans, 'w')
# 	
# 	np.write_files(gloss_f, trans_f, aln_f, ha_g_f, ha_t_f, morphs=False)
		
			
			
	
		