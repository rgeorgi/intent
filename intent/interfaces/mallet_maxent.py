'''
Created on Apr 4, 2014

@author: rgeorgi
'''
import os
import subprocess as sub
import sys
from classify.Classification import Classification
from utils.TwoLevelCountDict import TwoLevelCountDict
import re
from _io import StringIO
import igt.grams
from utils.token import GoldTagPOSToken
from utils.setup_env import c

class ClassifierException(Exception):
	pass

class EmptyStringException(ClassifierException):
	pass


class MalletMaxent(object):
	
	def __init__(self, model):
		self._model = model
		
		mallet = c['mallet']
		
		mallet_bin = os.path.join(os.path.join(mallet, 'bin'), 'mallet')
		
		self.c = sub.Popen([mallet_bin, 
							'classify-file',
							'--classifier', self._model,
							'--input', '-',
							'--output', '-'],
				stdout=sub.PIPE, stdin=sub.PIPE, stderr=sys.stderr)
		self._first = True
		
	def info(self):
		'''
		Print the feature statistics for the given model. (Assumes MaxEnt)
		'''
		mallet = c['mallet']
		info_bin = os.path.join(os.path.join(mallet, 'bin'), 'classifier2info')
		info_p = sub.Popen([info_bin, '--classifier', self._model],
							stdout=sub.PIPE, stdin=sub.PIPE, stderr=sub.PIPE)
		
		cur_class = None
		feats = TwoLevelCountDict()
		
		# Go through and pick out what the features are for
		for line in info_p.stdout:
			content = line.decode(encoding='utf-8')
			
			class_change = re.search('FEATURES FOR CLASS (.*)', content)			
			# Set the current class if the section changes
			if class_change:
				cur_class = class_change.group(1).strip()
				continue
			
			# Otherwise, let's catalog the features.
			word, prob = content.split()
			feats.add(cur_class, word, float(prob))
			
		# Now, print some info
		for cur_class in feats.keys():
			print(cur_class, end='\t')
			print('%s:%.4f' % ('<default>', feats[cur_class]['<default>']), end='\t')
			top_10 = feats.top_n(cur_class, n=10, key2_re='^nom')
			print('\t'.join(['%s:%.4f' % (w,p) for w,p in top_10]))
				
	def classify_string(self, s, **kwargs):
		'''
		Run the classifier on a string, breaking it apart as necessary.
		
		:param s: String to classify
		:type s: str
		'''

		token = GoldTagPOSToken(s, goldlabel="NONE")
		
		sio = StringIO()
		
		# TODO: Fix the behavior of write_gram such that we can just do it from a string.
		igt.grams.write_gram(token, type='classifier', output=sio, **kwargs)
		
		c_token = sio.getvalue().strip()
		sio.close()
		
		result = self.classify(c_token)
		return result 
	
	def classify_token(self, token, **kwargs):
		
		token = GoldTagPOSToken.fromToken(token, goldlabel='NONE')
		
		sio = StringIO()
		igt.grams.write_gram(token, type='classifier', output=sio, **kwargs)
		c_token = sio.getvalue().strip()
		sio.close()
		
				
		result = self.classify(c_token)
		
		return result
		
				
		
	def classify(self, string):
		if not string.strip():
			raise EmptyStringException('Empty string passed into classify.') 
		else:
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
			
			
			#print(string, content)
			
			for i in range(1, len(content), 2):
			
				tag = content[i]
				
				prob = float(content[i+1])
				ret_c[tag] = float(prob)
				
			return ret_c
		
		
		
		
	
	def close(self):
		self.c.kill()

if __name__ == '__main__':
	mc = MalletMaxent('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/all/xigt_grams.maxent')
	mc.info()