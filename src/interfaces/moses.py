#!/usr/bin/env python

import os, sys, re
import argparse
from utils.ConfigFile import ConfigFile

def align(moses_bin, bin_dir, e_file, f_file):
	os.system('%s --parallel -external-bin-dir %s --corpus . --f gloss -e trans' % (moses_bin, bin_dir))

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('c', metavar='CONFIG')
	
	args = p.parse_args()
	
	c = ConfigFile(args.c)
	
	align(c['moses_bin'], c['bin_dir'], c['e_file'], c['f_file'])