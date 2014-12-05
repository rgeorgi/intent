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
from subprocess import Popen, PIPE, STDOUT
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
		
		
	def train_txt(self, txt, model, log_f = sys.stdout):
		'''
		Get info from the given classifier
		'''
		
		ntf = NamedTemporaryFile(mode='w', delete=False)
		ntf.close()
		
		# Start by converting the given text file to a vector
		p = Popen([self.bin, 'import-svmlight', '--input', txt, '--output', ntf.name])
		
		log_f.write('Converting to SVM light at temp file: %s\n' % ntf.name)
		log_f.write('-'*80+'\n')
		
		p.wait()
		
		cmd = '%s ' % self.bin
		
		cmd += 'train-classifier '
		cmd += '--input %s ' % ntf.name
		cmd += '--trainer MaxEntTrainer '
		#cmd += '--help '

		
		if model:
			cmd += '--output-classifier %s ' % model
		else:
			cmd += '--training-portion 0.9 '
			cmd += '--random-seed 6 '
		
		log_f.write(cmd+'\n')
		
		p = Popen(cmd.split(), stdout=PIPE, stderr=STDOUT)
		while p.poll() == None:
			content = p.stdout.read(1)
			log_f.write(content.decode('utf-8'))
			
		p.wait()
		
		if not model:
			output = p.stdout.read().decode(encoding='utf-8')
			training = float(re.search('train accuracy mean = ([0-9\.]+)', output).group(1))
			testing = float(re.search('test accuracy mean = ([0-9\.]+)', output).group(1))

		#os.remove(ntf.name)
		
		if not model:
			return (training, testing)
		
			
			
			
		
		
		
		
		