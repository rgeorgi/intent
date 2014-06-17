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
from utils.argutils import ArgPasser
from unittest.case import TestCase
from tempfile import NamedTemporaryFile
import os


class ConfigFileException(Exception):
	def __init__(self, m = None):
		Exception.__init__(self, m)
		
		
class NoOptionException(ConfigFileException):
	def __init__(self, m = None):
		ConfigFileException.__init__(self, m)
		
class SetConflict(ConfigFileException):
	def __init__(self, m = None):
		ConfigFileException.__init__(self, m)

class ConfigFile(ArgPasser):
	def __init__(self, path):
				
		cf = open(path, 'rb')
		lines = cf.readlines()
		for line in lines:
			line = line.decode('unicode_escape')
			content = re.search('(^[^#]*)', line).group(1).strip()
			
			# Skip blank or commented lines
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
				if refname in self:
					string = string.replace(ref, self[refname])
					
			string = string.replace('"', '')
			
			#===================================================================
			# Attempt to evaluate the strings.
			#===================================================================
			try:
				string = eval(string)
			except Exception as e:
				pass
					
			self[var] = string
		

	def set_defaults(self, dict):
		for key in dict:
			self.set(key, dict[key], overwrite = False)


#===============================================================================
# Test Cases
#===============================================================================

class ConfigFileTests(TestCase):
	
	def setUp(self):
		self.nt = NamedTemporaryFile('w', delete=False)
		self.nt.write('''
# This is a test config file.
a = True
b = 0
c = 1
d = False

e = "quoted string"
f = $e "also this"

		''')
		self.nt.close()
		self.cf = ConfigFile(self.nt.name)
		
	def tearDown(self):
		os.remove(self.nt.name)
		
		
	def testBool(self):
		cf = self.cf
		
		self.assertIs(cf['a'], True)
		self.assertIs(cf['d'], False)
		self.assertIs(cf['b'], 0)
		
		self.assertFalse(cf['b'])
		self.assertFalse(cf['d'])
		
		self.assertTrue(cf['a'])
		self.assertTrue(cf['c'])
		
	def testRefs(self):
		cf = self.cf
		self.assertEqual(cf['e'], "quoted string")
		self.assertEqual(cf['f'], "quoted string also this")