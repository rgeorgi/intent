'''
Created on Oct 24, 2013

@author: rgeorgi
'''
import os

def remove_safe(path):
	if os.path.exists(path):
		os.remove(path)