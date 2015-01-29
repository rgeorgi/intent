'''
Created on Dec 19, 2014

@author: rgeorgi

This script is used to point at a dump of the ODIN database and extract the specified language from it.
'''
import argparse
from utils.argutils import configfile, writefile
from utils.fileutils import matching_files
import re
import sys

def extract_lang(dir, lang, outfile):
	
	i = 0
	
	# Iterate through each ".check" file in the given directory.
	for path in matching_files(dir, '.*\.check$', recursive=True):
		
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
			
			inst_lang = None
			# First, if there is a "gold" lang code, use that one.
			gold_re = re.search('gold_lang_code:.*?\(([a-z:]+)\)', instance, flags=re.I)
			chosen_re = re.search('stage3_lang_chosen:.*?\(([a-z:]+)\)', instance, flags=re.I)
						
			if gold_re:
				inst_lang = gold_re.group(1)
				
			elif chosen_re:			
				inst_lang = chosen_re.group(1)
				
			if inst_lang == lang:
				outfile.write(instance+'\n\n')
				i += 1
				
	print('%d instances written.' % i)
	outfile.close()
			

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	
	p.add_argument('-c', '--config', type=configfile)
	p.add_argument('-d', '--dir', help="Path to the ODIN database directory.", required=True)
	p.add_argument('-l', '--lang', help="Language to search for.", required=True)
	p.add_argument('-o', '--outfile', help="Text file which to output the resulting instances to.", required=True, type=writefile)
	
	args = p.parse_args()
		
	extract_lang(args.dir, args.lang, args.outfile)