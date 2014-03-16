#!/usr/bin/env python

from xigt.codecs import xigtxml
import argparse
from corpora.IGTCorpus import IGTInstance, IGTTier
from xigt.core import Tier, Item
from utils.string_utils import tokenize_string
import sys

def xigt_process(xigt_corpus):
	'''
	Process IGT and add alignment info.
	
	@param xigt_corpus:
	'''
	
	for inst in xigt_corpus.igts:
		cleaned = [t for t in inst.tiers if t.type == 'odin-clean']
		for c in cleaned:			
			glosses = [g.content for g in c.items if g.attributes['tag'] == 'G']
			trans = [t.content for t in c.items if t.attributes['tag'] == 'T']
			
			if glosses and trans:
				i = IGTInstance(id=inst.id)
				g = IGTTier.fromString(glosses[0], kind='gloss')
				t = IGTTier.fromString(trans[0], kind='trans')
				i.append(g)
				i.append(t)
				
				aln = i.gloss_heuristic_alignment()
				
				# Add a gloss tier.
				gloss_tier = Tier(id='g', type='glosses', attributes={'content':'c', 'alignment':'t'})
				trans_tier = Tier(id='t', type='translations', attributes={'content':'c'})
				
				
				# Tokenize the stings, with a tokenizer that returns spans
				trans_tokens = tokenize_string(trans[0])
				gloss_tokens = tokenize_string(glosses[0])
				
				# Add each of the translation tokens to the list
				for t_i in range(len(trans_tokens)):
					trans_token = trans_tokens[t_i]
					start, end = trans_token.span
					attrs = {'content':'{}[{}:{}]'.format(c.id, start, end),
							'form':trans_token.seq}
					trans_tier.add(Item(id='t%d'%(t_i+1), attributes=attrs))
								
				
				# Add each of the gloss tokens to the list.
				for g_i in range(len(gloss_tokens)):
					gloss_token = gloss_tokens[g_i]
					start, end = gloss_token.span
					
					#===========================================================
					# Get the alignments for the given token.
					#===========================================================
					alns = [a[1] for a in aln.aln if a[0] == g_i+1]
					alns.sort()
					alns = ['t'+str(a) for a in alns]
										
					
					attrs = {'content':'{}[{}:{}]'.format(c.id, start, end),
							 'form':gloss_token.seq}
					
					if alns:
						attrs['alignment'] = '%s' % ','.join(alns)
					
					gloss_tier.add(Item(id='g%d'%(g_i+1), attributes=attrs))
					
				# Add the tiers to the instance
				inst.add(gloss_tier)
				inst.add(trans_tier)
				
				# Now, add the alignents
# 				for a_g_i, t_g_i in aln.aln:
# 					print(gloss_tier.get('g%d'%a_g_i))
					
					
					
								

				
	xigtxml.dump(sys.stdout, xigt_corpus, pretty_print=True)
			

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('xml')
	
	args = p.parse_args()
	
	xigt_corpus = xigtxml.load(args.xml)
	xigt_process(xigt_corpus)