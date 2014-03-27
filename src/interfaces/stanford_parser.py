#!/usr/bin/env python
'''
Created on Oct 23, 2013

@author: rgeorgi
'''
import os
from tempfile import NamedTemporaryFile
import sys
from utils.ConfigFile import ConfigFile


def prop():
	global parser_jar, model
	mydir = os.path.abspath(os.path.dirname(__file__))
	c = ConfigFile(os.path.join(mydir, 'stanford_parser.prop'))
	javahome = c['javahome']
	
	os.environ.putenv('JAVAHOME', javahome)
	parser_jar = c['jar']
	model = c['eng_model']

def parse_file(filename):
	prop()
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

if __name__ == '__main__':
	prop()
	parse_lines([])