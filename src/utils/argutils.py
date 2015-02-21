'''
Created on Aug 26, 2013

@author: rgeorgi
'''
import sys, os
from unittest import TestCase
from .ConfigFile import ConfigFile
from utils.ConfigFile import ConfigFileException

def require_opt(option, msg, must_exist = False, must_exist_msg = 'The file "%s" was not found\n'):
	errors = False
	if not option:
		sys.stderr.write('ERROR: %s\n'%msg)
		errors = True
	elif must_exist and not os.path.exists(option):
		sys.stderr.write('ERROR: '+must_exist_msg % option)
		errors = True
	return errors

#===============================================================================
# Exceptions
#===============================================================================
class CommandLineException(Exception):
	pass

class FileNotExistsException(CommandLineException):
	pass

class DirNotExistsException(CommandLineException):
	pass

#===============================================================================
# Argparse Types
#===============================================================================

def exists(path):
	'''
	Type for passing to argparse to verify that the argument is an extant path.
	'''
	if not os.path.exists(path):
		raise CommandLineException('Path "%s" does not exist' % path)
	else:
		return path

def existsfile(path):
	'''
	Type for passing to argparse to verify that the argument both:
	
	- Is a file
	- Exists on the filesystem
	'''
	if not os.path.exists(path):
		raise CommandLineException('File "%s" does not exist.' % path)
	elif not os.path.isfile(path):
		raise CommandLineException('Path "%s" is not a file.' % path)
	else:
		return path
	
def existsdir(path):
	'''
	Type for passing to argparse to verify that the argument both:
	
	- Is a directory
	- Exists on the filesystem
	'''
	if not os.path.exists(path):
		raise CommandLineException('Directory "%s" does not exist.' % path)
	if not os.path.isdir(path):
		raise CommandLineException('Path "%s" is not a directory.' % path)
	else:
		return path
	
	
def configfile(path):
	c = existsfile(path)
	return ConfigFile(c)

def writedir(path):
	os.makedirs(path, exist_ok=True)
	return path

	
def writefile(path, mode='w', encoding='utf-8'):
	'''
	Ensure that this file is writable in the given path, and return it as an 
	open file object.
	
	:param path: Path to the file to write
	:type path: filepath
	:param mode: Write mode
	:type mode: [ 'w' | 'wb' ]
	:param encoding: File encoding 
	:type encoding: encoding
	'''
	dir = os.path.dirname(path)

	if dir and not os.path.exists(dir): 
		os.makedirs(dir, exist_ok=True)

	try:
		f = open(path, mode, encoding=encoding)
	except Exception as e:
		raise e
	
	return f
	
