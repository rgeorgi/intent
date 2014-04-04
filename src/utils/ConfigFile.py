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
from _abcoll import Mapping, MutableMapping




class ConfigFileException(Exception):
	def __init__(self, m = None):
		Exception.__init__(self, m)
		
		
class NoOptionException(ConfigFileException):
	def __init__(self, m = None):
		ConfigFileException.__init__(self, m)
		
class SetConflict(ConfigFileException):
	def __init__(self, m = None):
		ConfigFileException.__init__(self, m)

class ConfigFile(MutableMapping):
	def __init__(self, path):
		
		self._settings = {}
		
		cf = open(path, 'rb')
		lines = cf.readlines()
		for line in lines:
			line = line.decode('unicode_escape')
			content = re.search('(^[^#]*)', line).group(1).strip()
			if not content:
				continue
			try:
				var, string = content.split('=')
				var = var.strip()
				string = string.strip()
			except ValueError as ve:
				sys.stderr.write(content+'\n')
				raise ve
			
			
			
			# Go ahead and replace all backreferences...
			refs = re.findall('"?(\$\w+)"?', string)
			for ref in refs:
				refname = ref[1:]
				if refname in self._settings:
					string = string.replace(ref, self._settings[refname])
			string = string.replace('"', '')
					
			# Try to parse the right-hand side into the appropriate element.
			try:
# 				string = eval(string)
				pass
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
		
	def __setitem__(self, k, v):
		self.settings[k] = v
		
	def __iter__(self):
		return self.settings.__iter__()
	
	def __len__(self):
		return len(self.settings)

	def set_defaults(self, dict):
		for key in dict:
			self.set(key, dict[key], overwrite = False)

	def __delitem__(self, k):
		self.settings.__delitem__(k)
				
	def set(self, key, value, overwrite = False):
		if overwrite or key not in self._settings:
			self._settings[key] = value
		
	def getint(self, k):
		if k not in self._settings:
			raise NoOptionException(k)
		else:
			return int(self[k])
		
	def get(self, k, default=None):
		if k not in self._settings:
			return default
		else:
			return self._settings[k]
		
	@property
	def settings(self):
		return self._settings
			
