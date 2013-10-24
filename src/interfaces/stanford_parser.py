#!/usr/bin/env python
'''
Created on Oct 23, 2013

@author: rgeorgi
'''
from ConfigParser import ConfigParser
import os
from tempfile import NamedTemporaryFile
import sys, jpype

def prop():
	global parser_jar
	c = ConfigParser()
	mydir = os.path.abspath(os.path.dirname(__file__))
	c.read(os.path.join(mydir, 'stanford_parser.prop'))	
	parser_jar = c.get('stanford', 'jar')

def parse_file(filename):
	prop()
	global parser_jar
	model_path = '/Users/rgeorgi/Dropbox/code/eclipse/stanford-parser/models/englishFactored.ser.gz'
	os.system('java -Xmx500m -cp %s edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat "penn,typedDependencies" %s %s' % (parser_jar, model_path, filename))


def parse_lines(inlines):
	global parser_jar


	infile = NamedTemporaryFile()
	for line in inlines:
		infile.write(line+'\n')
	infile.flush()
	
	parse_file(infile.name)
	
	infile.close()

if __name__ == '__main__':
	prop()
	parse_lines([])