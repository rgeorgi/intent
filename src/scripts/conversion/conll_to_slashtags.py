'''
Created on Sep 12, 2014

@author: rgeorgi
'''
import argparse
import os
from treebanks.conll.ConllParser import ConllParser
from corpora.POSCorpus import POSCorpus

def conll_to_slashtags(infiles, outpath):
	main_c = POSCorpus()
	for f in infiles:
		cp = ConllParser()
		c = cp.parse_file(root=f)
		main_c.extend(c)
	
	st = c.slashtags('/', lowercase=True)
	of = open(outpath, 'w', encoding='utf-8')
	of.write(st)
	of.close()
	

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument(metavar='FILE', dest='filelist', nargs='+')
	p.add_argument('-o', dest='outpath', required=True)
	
	args = p.parse_args()
	
	conll_to_slashtags(args.filelist, args.outpath)
	
	