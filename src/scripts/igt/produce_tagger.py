'''
Created on Feb 20, 2015

@author: rgeorgi
'''
import argparse
from utils.argutils import existsfile, writefile
from igt.rgxigt import RGCorpus
from utils.argpasser import ArgPasser, argp
from utils.setup_env import c
from interfaces.stanford_tagger import StanfordPOSTagger
from interfaces.mallet_maxent import MalletMaxent
import sys


classification = 'classification'

heur_proj      = 'heur-proj'
giza_proj      = 'giza-proj'
giza_direct    = 'giza-proj-direct'

projection     = [heur_proj, giza_proj, giza_direct]
normal_proj    = [giza_proj, heur_proj]
giza           = [giza_proj, giza_direct]

UNK            = 'UNK'

class TagProductionException(Exception): pass



@argp
def produce_tagger(inpath, out_f, method, kwargs = None):
	
	if kwargs.get('xc'):
		xc = kwargs.get('xc')
	else:
		# Load the xigt corpus.
		xc = RGCorpus.load(inpath)
	
	# Before reducing the size of the corpus, filter out
	# instances missing translation lines if we are projecting
	if method in projection:
		old_len = len(xc)
		xc.require_trans_lines()
		new_len = len(xc)
		
		filtered = old_len - new_len
	
	
	
	limit = kwargs.get('limit', 0, int)
	if limit:
		xc.igts = xc.igts[:limit]
		xc.refresh_index()
		
	skipped = 0
	
	# Giza Realignment ---------------------------------------------------------
	# If we are using a giza based approach, we will want to
	# realign the corpus now, since it is heuristic by default.
	if method == giza_proj:
		xc.giza_align_t_g(kwargs.get('resume'))
		
	elif method == giza_direct:
		xc.giza_align_l_t()
	
	for i, inst in enumerate(xc):
		
		if i % 25 == 0:
			print('Processing instance %d' % i)

		# If we are doing classification
		if method == classification:
			inst.classify_gloss_pos(kwargs.get('classifier'))
			inst.project_gloss_to_lang()
			
		# If we are doing normal projection via the gloss line
		elif method in normal_proj:
			inst.project_trans_to_gloss()
			inst.project_gloss_to_lang()
			
		# Otherwise, we are looking at doing the direct translation
		# to language based approach.
		elif method == giza_direct:
			inst.project_trans_to_lang()
			
		# Raise an exception if we somehow got a different method.
		else:
			raise TagProductionException('Method "%s" is not defined for producing taggers.' % method)
		
			
		# Whichever method, get the gloss line tags:
		sequence = inst.get_lang_sequence()
		
		# If we get a "skip" and "UNK" appears in the sequence...
		if kwargs.get('skip') and len(sequence) != len([i for i in sequence if i.label != UNK]):
			skipped += 1
			continue
	
		else:
			# Replace the "UNK" with "NOUN"			
			for pos_token in sequence:				
				if pos_token.label == 'UNK' and kwargs.get('replace_unknown'):
					pos_token.label = "NOUN"
				
				out_f.write('%s/%s ' % (pos_token.seq, pos_token.label))
			out_f.write('\n')
			out_f.flush()
			
	out_f.close()
	return skipped
		
		
		

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-i', '--input', required=True, type=existsfile, help='Existing xigt xml file.')
	p.add_argument('-o', '--output', required=True, type=writefile, help='Output slashtag format file.')
	p.add_argument('-m', '--method', choices=['classification','heur-proj','giza-proj', 'giza-proj-direct'])
	p.add_argument('-s', '--skip', action='store_true', help='Whether to skip incomplete projections or not.')
	p.add_argument('-l', '--limit', type=int, default=0, help='limit the number of sentences used in the resulting file')
	
	args = p.parse_args()
	ap = ArgPasser(vars(args))
	del ap['method']
	del ap['output']
	
	classifier = None
	tagger = None
	
	if args.method not in projection:
		ap['classifier'] = MalletMaxent(c['classifier_model'])
		
	produce_tagger(args.input, args.output, args.method, **ap)