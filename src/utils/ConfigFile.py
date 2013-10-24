'''
Created on Oct 23, 2013

@author: rgeorgi

Basic config file. Comments and blank lines are ignored. 

Variables are stored in a dictionary.

Supports '$' references, as long as they are ordered correctly.

Also automatically attempts to parses lines into python types (lists, integers).
'''
import re
import sys

class ConfigFile():
	def __init__(self, path):
		
		self._settings = {}
		
		cf = file(path, 'r')
		lines = cf.readlines()
		for line in lines:
			content = re.search('(^[^#]*)', line).group(1).strip()
			if not content:
				continue
			try:
				var, string = content.split('=')
				var = var.strip()
				string = string.strip()
			except ValueError as ve:
				sys.stderr.write(content)
				raise ve
			
			
			
			# Go ahead and replace all backreferences...
			refs = re.findall('\$\w+', string)
			for ref in refs:
				refname = ref[1:]
				if refname in self._settings:
					string = string.replace(ref, self._settings[refname])
					
			# Try to parse the right-hand side into the appropriate element.
			try:
				string = eval(string)
			except:
				pass
			try:
				string = int(string)
			except:
				pass
			
			self._settings[var] = string

	def __getitem__(self, k):
		if k in self._settings:
			return self._settings[k]
		else:
			return None
