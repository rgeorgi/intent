'''
Created on Oct 1, 2014

@author: rgeorgi
'''
from tempfile import NamedTemporaryFile

'''
Created on Jun 12, 2014

@author: rgeorgi
'''
import os
from interfaces.MalletTool import MalletTool
from subprocess import Popen, PIPE
import sys
from utils.TwoLevelCountDict import TwoLevelCountDict
import re

class MalletMaxentTrainer(MalletTool):
	'''
	classdocs
	'''

	def __init__(self):		
		MalletTool.__init__(self)
		self.bin = os.path.join(self.mallet, 'bin/mallet')		
		
		
	def train_txt(self, txt, model):
		'''
		Get info from the given classifier
		'''
		
		ntf = NamedTemporaryFile(mode='w', delete=False)
		ntf.close()
		
		# Start by converting the given text file to a vector
		p = Popen([self.bin, 'import-svmlight', '--input', txt, '--output', ntf.name])
		print(ntf.name)
		
		p.wait()
		
		p = Popen([self.bin, 'train-classifier', '--input', ntf.name, '--trainer', 'MaxEntTrainer', '--training-portion', '0.9', '--random-seed', '6'], stdout=PIPE)

		
		p.wait()
		output = p.stdout.read().decode(encoding='utf-8')
		training = float(re.search('train accuracy mean = ([0-9\.]+)', output).group(1))
		testing = float(re.search('test accuracy mean = ([0-9\.]+)', output).group(1))

		os.remove(ntf.name)
		
		return (training, testing)
		
			
			
			
		
		
		
		
		