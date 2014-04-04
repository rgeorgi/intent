'''
Created on Apr 4, 2014

@author: rgeorgi
'''
import os
from utils.ConfigFile import ConfigFile
import subprocess as sub
import sys
from classify.Classification import Classification

def setup():
	global mallet
	mydir = os.path.abspath(os.path.dirname(__file__))
	c = ConfigFile(os.path.join(mydir, 'mallet_maxent.prop'))
	
	mallet = c['mallet']

class MalletClassifier(object):
	
	def __init__(self, model):
		self._model = model
		setup()
		mallet_bin = os.path.join(os.path.join(mallet, 'bin'), 'mallet')
		
		
		self.c = sub.Popen([mallet_bin, 
							'classify-file',
							'--classifier', self._model,
							'--input', '-',
							'--output', '-'],
				stdout=sub.PIPE, stdin=sub.PIPE, stderr=sys.stderr)
		self._first = True
		
	def classify(self, string):
		self.c.stdin.write(bytes(string+'\r\n\r\n', encoding='utf-8'))
		self.c.stdin.flush()
		if self._first:
			content = self.c.stdout.readline()
			self._first = False
		else:
			self.c.stdout.readline()
			content = self.c.stdout.readline()
			
		content = content.decode(encoding='utf-8')
		
		content = content.split()
		ret_c = Classification(gold=content[0])
		
		for i in range(1, len(content[1:]), 2):
			tag = content[i]
			prob = float(content[i+1])
			ret_c[tag] = prob
			
		return ret_c
		
		
		
		
	
	def close(self):
		self.c.kill()

if __name__ == '__main__':
	mc = MalletClassifier('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/all/xigt_grams.maxent')
	mc.classify('NOUN this:1 is:1 a:1')
	mc.classify('VERB this:1 1sg:1 a:1')