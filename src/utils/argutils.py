'''
Created on Aug 26, 2013

@author: rgeorgi
'''
import sys, os
from unittest import TestCase

def require_opt(option, msg, must_exist = False, must_exist_msg = 'The file "%s" was not found\n'):
	errors = False
	if not option:
		sys.stderr.write('ERROR: %s\n'%msg)
		errors = True
	elif must_exist and not os.path.exists(option):
		sys.stderr.write('ERROR: '+must_exist_msg % option)
		errors = True
	return errors


class CommandLineException(Exception):
	pass

class FileNotExistsException(CommandLineException):
	pass

class DirNotExistsException(CommandLineException):
	pass

def exists(path):
	if not os.path.exists(path):
		raise CommandLineException('Path "%s" does not exist' % path)
	else:
		return path

def existsfile(path):
	if not os.path.exists(path):
		raise CommandLineException('File "%s" does not exist.' % path)
	elif not os.path.isfile(path):
		raise CommandLineException('Path "%s" is not a file.' % path)
	else:
		return path
	
def existsdir(path):
	if not os.path.exists(path):
		raise CommandLineException('Directory "%s" does not exist.' % path)
	if not os.path.isdir(path):
		raise CommandLineException('Path "%s" is not a directory.' % path)
	else:
		return path
	
#===============================================================================
# ArgPasser
#===============================================================================

class ArgPassingException(Exception):
	pass

class ArgPasser(dict):
	'''
	Argpasser is just a drop-in replacement for a **kwarg dict,
	but allows for things that evaluate to false in the dict
	to be returned without being replaced by the default.
	'''
	
	def __init__(self, d):
		super().__init__(d)		
	
	def get(self, k, default=None, t=None):

		# Only replace with default if the key is actually
		# not in the mapping, not just evaluates to nothing.
		if k in self:
			val = self[k]
		else:
			val = default 
			
			
		
		# Parse val as the given type
		if t:
			try:
				val = t(val)
			except Exception as e:
				raise ArgPassingException(e)
			
		return val
			

#===============================================================================
#  TEST CASES
#===============================================================================
			
class ArgPasserTests(TestCase):
	
	def setUp(self):
		self.ap = ArgPasser({'a':1,
			 'b':'True',
			 'c':'2',
			 'd':0})
	
	def testBool(self):

		ap = self.ap
		self.assertIsNot(ap.get('b'), True)
		self.assertIs(ap.get('b', t=bool), True)
		self.assertTrue(ap.get('a'))
		self.assertFalse(ap.get('d', t=bool))
		
	def testInt(self):
		ap = self.ap
		self.assertEqual(ap.get('a'), 1)
		self.assertIsNot(ap.get('c'), 2)
		self.assertIs(ap.get('c', t=int), 2)