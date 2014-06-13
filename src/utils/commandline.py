'''
Created on Aug 26, 2013

@author: rgeorgi
'''
import sys, os

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