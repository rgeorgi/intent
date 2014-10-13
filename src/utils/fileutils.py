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
	
	# Get absolute paths for all the current files.
	paths = [os.path.join(dirpath, p) for p in os.listdir(dirpath)]
	
	# Find all the matching paths in the directory.
	files = [f for f in paths if os.path.isfile(f) and re.match(pattern, os.path.basename(f))]

			
	dirs = [d for d in paths if os.path.isdir(d)]
	
	
	
	
	if recursive:
		for dir in dirs:
			files.extend(matching_files(dir, pattern, recursive))
	
	return files

def globlist(globlist):
	retlist = []
	for globpattern in globlist:
		retlist.extend(glob.glob(globpattern))
	return retlist