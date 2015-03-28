#!/usr/bin/env python
'''
Created on Oct 23, 2013

@author: rgeorgi
'''

# Built-in imports -------------------------------------------------------------
import os, sys, logging
from tempfile import NamedTemporaryFile

# Internal Imports -------------------------------------------------------------
from intent.utils.env import parser_jar, parser_model, parser_model_jar
from intent.utils.systematizing import ProcessCommunicator
from unittest.case import TestCase

# NLTK Import
from intent.trees import XigtTree
from intent.igt.rgxigt import RGWordTier


# Set up the parser logger -----------------------------------------------------
PARSE_LOG = logging.getLogger('STANFORD_PARSER')

def parser_stderr_handler(msg):
	PARSE_LOG.warn(msg)

class ParseResult(object):
	def __init__(self):
		self.pt = None
		self.dt = None

class StanfordParser(object):
	'''
	Instantiate an object which can be called upon to return either phrase structure parses or
	dependency parses.
	'''
	def __init__(self):
		print(parser_jar)
		self.p = ProcessCommunicator(['java', '-Xmx500m',
										'-cp', parser_jar+':'+parser_model_jar,
										'edu.stanford.nlp.parser.lexparser.LexicalizedParser',
										'-outputFormat', 'penn,typedDependencies',
										'-sentences', 'newline',
										parser_model,
										'-'], stderr_func=parser_stderr_handler)
	
	def parse(self, string, id_base = None):
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
					result.pt = XigtTree.fromstring(string, id_base = id_base)
					string = ''
					
			string += line+' '
			
		return result
			
		
if __name__ == '__main__':
	sp = StanfordParser()
	wt = RGWordTier.from_string('The man ran', type='words', alignment='t', id='tw')
	wt.parse_pt(sp)

class ParseTest(TestCase):
	
	def setUp(self):
		self.sp = StanfordParser()
		print(self.sp.parse('This is a test').dt)
		print(self.sp.parse('John ran').pt)
	
	def basic_test(self):
		pass