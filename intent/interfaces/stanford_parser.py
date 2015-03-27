#!/usr/bin/env python
'''
Created on Oct 23, 2013

@author: rgeorgi
'''

# Built-in imports -------------------------------------------------------------
import os, sys, logging
from tempfile import NamedTemporaryFile

# Internal imports 
from intent.utils.env import parser_jar, parser_model, parser_model_jar
from intent.utils.systematizing import ProcessCommunicator
from unittest.case import TestCase


# Set up the parser logger -----------------------------------------------------
PARSE_LOG = logging.getLogger('STANFORD_PARSER')

def parser_stderr_handler(msg):
	PARSE_LOG.warn(msg)
	print(msg)

class ParseResult(object):
	def __init__(self):
		self.pt = None
		self.dt = None

class StanfordParser(object):
	def __init__(self):
		print(parser_jar)
		self.p = ProcessCommunicator(['java', '-Xmx500m',
										'-cp', parser_jar+':'+parser_model_jar,
										'edu.stanford.nlp.parser.lexparser.LexicalizedParser',
										'-outputFormat', 'penn,typedDependencies',
										'-sentences', 'newline',
										parser_model,
										'-'], stderr_func=parser_stderr_handler)
	
	def parse(self, string):
		self.p.stdin.write(bytes(string+'\n', encoding='utf-8'))
		self.p.stdin.flush()
		
		result = ParseResult()
		string = ''
		
		while True:
			line = self.p.stdout.readline().decode('utf-8', errors='replace').strip()
			
			# If the line is empty, the first time that means we are switching from phrase structure to
			# dependency. Otherwise, we are done.
			if not line:
				
				if result.pt:
					result.dt = string
					break
				else:
					result.pt = string
					string = ''
					
			string += line+' '
			
		return result
			
		
		
		

def parse_file(filename):
	global parser_jar, model
	os.system('java -Xmx500m -cp %s edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat "penn,typedDependencies" %s %s' % (parser_jar, model, filename))


def parse_lines(inlines):
	global parser_jar


	infile = NamedTemporaryFile()
	for line in inlines:
		infile.write(line+'\n')
	infile.flush()
	
	parse_file(infile.name)
	
	infile.close()

class ParseTest(TestCase):
	
	def setUp(self):
		self.sp = StanfordParser()
		print(self.sp.parse('This is a test').dt)
		print(self.sp.parse('John ran').pt)
	
	def basic_test(self):
		pass