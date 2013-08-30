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