'''
Created on Dec 19, 2014

@author: rgeorgi

This script is used to point at a dump of the ODIN database and
extract gloss and translation lines to align with MGIZA++.
'''
import argparse
from utils.argutils import configfile, writefile, writedir, existsfile,\
	existsdir
from utils.fileutils import matching_files
import re
import sys
from utils.setup_env import c
from corpora.IGTCorpus import IGTInstance, IGTParseException,\
	IGTParseExceptionLang, IGTParseExceptionGloss, IGTParseExceptionTrans

def extract_g_t(prefix):
	
	num_sents = 0
	
	odin_dir = c.get('odin_data', t=existsdir)
	
	# Open up the files for writing...
	g_f = open(prefix+'_g.txt', 'w', encoding='utf-8')
	t_f = open(prefix+'_t.txt', 'w', encoding='utf-8')
	
	# Iterate through each ".check" file in the given directory.
	for path in matching_files(odin_dir, '.*\.check$', recursive=True):
		
		# Open up the file... 
		f = open(path, 'r', encoding='latin-1')		
		data = f.read()
		f.close()
		
		# And get the list of instances.
		instances = re.split('\n\n+', data)
		
		# Remove blank "instances"
		instances = [i for i in instances if i.strip()]
		
		# Now, for each instance, look for the language.
		for instance in instances[1:]: # <-- skip the first pgph, because it's not an instance.
			
			try:
				i = IGTInstance.from_string(instance)
			except IGTParseExceptionLang as ipe:
				pass
			except IGTParseExceptionTrans as ipe:
				continue
			except IGTParseExceptionGloss as ipe:
				continue
		
			g_t = i.gloss.text()
			t_t = i.trans.text()
			
			# Break down by morph...
			for m in i.gloss.morphs():
				g_f.write(m.content.lower()+' ')
			g_f.write('\n')
			
			t_f.write(i.trans.text().lower()+'\n')
			
			g_f.flush()
			t_f.flush()
			
			num_sents += 1
				
	g_f.close()
	t_f.close()
	print('%d instances written.' % num_sents)
	
			

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	
	p.add_argument('-c', '--config', type=configfile)
	p.add_argument('-p', '--prefix', help="Prefix which to output the resulting text files with.", required=True)
	
	args = p.parse_args()

	extract_g_t(args.prefix)