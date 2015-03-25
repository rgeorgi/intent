'''
Created on Nov 14, 2014

@author: rgeorgi
'''

# built-in imports -------------------------------------------------------------
from argparse import ArgumentParser

# Internal Imports -------------------------------------------------------------

from intent.corpora.POSCorpus import POSCorpus
from intent.utils.argutils import existsfile
from intent.tagging.features import SequenceFeature

def slashtags_to_simpletagger(in_path, out_path):
	p = POSCorpus.read_slashtags(in_path)
	
	out_f = open(out_path, 'w', encoding='utf-8')
	
	for inst in p:
		sf = SequenceFeature(inst)
		while sf:			
						
			out_f.write('%s ' % sf.form)
						
# 			out_f.write('word-%s ' % sf.form)
# 			out_f.write('pre-3-%s ' % sf.prefix(3))
# 			out_f.write('pre-2-%s ' % sf.prefix(2))
# 			
# 			out_f.write('suf-3-%s ' % sf.suffix(3))
# 			out_f.write('suf-2-%s ' % sf.suffix(2))
# 			
# 			#===================================================================
# 			# Context Features
# 			#===================================================================
# 			out_f.write('prev-%s ' % sf.prev().form)
# 			out_f.write('next-%s ' % sf.next().form)
# 			
# 			#===================================================================
# 			# More Context
# 			#===================================================================
# 			out_f.write('prev-prev-%s ' % sf.prev().prev().form)
# 			out_f.write('next-next-%s ' % sf.next().next().form)
			
			# Finally, write out the label
			out_f.write('%s\n' % sf.label)			
			
			sf = sf.next()
		out_f.write('\n')
		
	out_f.close()
			
		

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-i', '--input', type=existsfile, required=True)
	p.add_argument('-o', '--output', required=True)
	
	args = p.parse_args()
	
	slashtags_to_simpletagger(args.input, args.output)
	