'''
Created on Oct 24, 2013

@author: rgeorgi
'''
import os
import re
import sys
import glob

def remove_safe(path):
	if os.path.exists(path):
		os.remove(path)
		
def matching_files(dirpath, pattern, recursive=False):
	'''
	Return the paths matching a pattern in a directory, optionally recurse
	into the subdirectories.
	
	@param dirpath: directory to scan
	@param pattern: regular expression to match paths upon
	@param recursive: whether or not to recurse into the directories.
	'''
	paths = os.listdir(dirpath)
	paths = map(lambda path: os.path.join(dirpath, path), paths)
	# Find all the matching paths in the directory.
	ret_list = filter(lambda f: os.path.isfile(f) and re.match(pattern, os.path.basename(f)), paths)

			
	dirs = filter(lambda d: os.path.isdir(d), paths)
	
	
	if recursive:
		for dir in dirs:
			ret_list.extend(matching_files(dir, pattern, recursive))
	
	return ret_list

def globlist(globlist):
	retlist = []
	for globpattern in globlist:
		retlist.extend(glob.glob(globpattern))
	return retlist