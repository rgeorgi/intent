'''
Created on Apr 30, 2014

@author: rgeorgi
'''

from treebanks.xaml import XamlParser
from argparse import ArgumentParser
from glob import glob
import os
import sys

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('dir', metavar='DIR', nargs='+')
	
	args = p.parse_args()
	
	xp = XamlParser.XamlParser()
	for dir in args.dir:
		xml_files = glob(os.path.join(dir, '*.xml'))
		for x_f in xml_files:				
			xp.parse(x_f)