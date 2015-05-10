'''
Created on Feb 20, 2015

@author: rgeorgi
'''

# Built-in imports -------------------------------------------------------------
import argparse
import os
import logging

# Internal imports -------------------------------------------------------------
from intent.utils.argutils import existsfile, writefile
from intent.igt.rgxigt import RGCorpus, ProjectionTransGlossException
from intent.utils.argpasser import ArgPasser, argp
from intent.utils.env import c
from intent.interfaces.mallet_maxent import MalletMaxent

#===============================================================================
# Set up logging
#===============================================================================

TAGLOG = logging.getLogger(__name__)

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
	
	corp_length = len(xc)
	
	# Before reducing the size of the corpus, filter out
	# instances lacking g/t alignment for classification and projection...
	if method == classification or method in normal_proj:
		xc.require_one_to_one()
		corp_length = len(xc)
	
	# Also, filter out instances where a translation line is missing
	# if we are projecting. (This overlaps with the above, but leaves
	# direct giza alignments to not require one to one alignment.)
	if method in projection:
		xc.require_trans_lines()
		corp_length = len(xc)
		

		
	limit = kwargs.get('limit', 0, int)
	if limit:
		xc.igts = xc.igts[:limit]
		corp_length = len(xc)
		
	
	# Giza Realignment ---------------------------------------------------------
	# If we are using a giza based approach, we will want to
	# realign the corpus now, since it is heuristic by default.
	if method == giza_proj:
		xc.giza_align_t_g(kwargs.get('resume'))
		
	elif method == giza_direct:
		xc.giza_align_l_t()
	
	TAGLOG.info('Producing tagfile for "%s"' % os.path.relpath(out_f.name))
	
	#===========================================================================
	# ADD PUNC
	#===========================================================================
	out_f.write('''./PUNC
?/PUNC
“/PUNC
"/PUNC
''/PUNC
'/PUNC
,/PUNC
…/PUNC
//PUNC
--/PUNC
``/PUNC
:/PUNC
;/PUNC
«/PUNC
»/PUNC
-/PUNC\n''')
	
	for i, inst in enumerate(xc):
		
		if i % 25 == 0:
			TAGLOG.info('Processing instance %d' % i)

		# If we are doing classification
		if method == classification:
			inst.classify_gloss_pos(kwargs.get('classifier'), posdict=kwargs.get('posdict'))
			inst.project_gloss_to_lang()
			
		# If we are doing normal projection via the gloss line
		elif method in normal_proj:
			try:
				inst.project_trans_to_gloss()
			except ProjectionTransGlossException as ptge:
				TAGLOG.warn(ptge)
				continue
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
			corp_length -= 1
			continue
	
		else:
			# Replace the "UNK" with "NOUN"			
			for i, pos_token in enumerate(sequence):				
				if pos_token.label == 'UNK' and kwargs.get('unk_nouns'):
					pos_token.label = "NOUN"
				elif pos_token.label == 'UNK' and kwargs.get('unk_classify'):
					classifier = kwargs.get('classifier')
					
					kwargs['prev_gram'] = ''
					kwargs['next_gram'] = ''
					
					if i > 0:
						kwargs['prev_gram'] = inst.gloss[i-1].get_content()
					if i < len(inst.gloss)-1:
						kwargs['next_gram'] = inst.gloss[i+1].get_content()
					
					pos_token.label = classifier.classify_string(inst.gloss[i].get_content(), **kwargs).largest()[0]
				
				
				out_f.write('%s/%s ' % (pos_token.seq, pos_token.label))
			out_f.write('\n')
			out_f.flush()
			
	out_f.close()
	return corp_length
		
		
		

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