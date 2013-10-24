'''
Created on Oct 23, 2013

@author: rgeorgi
'''
import re
from igt.IGT import IGT
from interfaces.stanford_parser import parse_lines
import sys



def parse_gloss(filename, seen_ids, sent_list):
	f = file(filename, 'r')
	lines = f.read()
	sents = re.findall('<Sent[\s\S]+?</Sent', lines)
	

	for sent in sents:
		id = re.search('id="(.*?)"', sent).group(1)
		if id in seen_ids:
			continue
		else:
			i = IGT()
			i.id = id
			i.trans = re.search('<Translation>(.*?)</Translation>', sent).group(1)
			i.lang = re.search('<Original>(.*?)</Original>', sent).group(1)
			i.gloss = re.search('<Gloss>(.*?)</Gloss>', sent).group(1)
			sent_list.append(i)
	f.close()

def gloss_parse():
	seen_ids = {}
	sents = []
	parse_gloss('/Users/rgeorgi/Documents/Work/treebanks/hindi_ds/Glosses-DSguidelines.txt', seen_ids, sents)
	parse_gloss('/Users/rgeorgi/Documents/Work/treebanks/hindi_ds/Glosses-PSguidelines.txt', seen_ids, sents)
	
	translations = []
	good_ids = []
	i = 0
	for sent in sents:
		if sent.trans.strip() == '??' or not sent.trans.strip():
			continue
		good_ids.append(sent.id)
		translations.append(sent.trans)
					
	
	parse_lines(translations)
	
		
	

if __name__ == '__main__':
	gloss_parse()