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

class MalletMaxentInfo(MalletTool):
	'''
	classdocs
	'''


	def __init__(self, fp):		
		MalletTool.__init__(self)
		self.fp = fp
		self.infotool = os.path.join(self.mallet, 'bin/classifier2info')
		
		self.feats = TwoLevelCountDict()
		
		
	def info(self):
		'''
		Get info from the given classifier
		'''
		
		# Open a java process to dump the classifier info
		p = Popen([self.infotool, '-Xmx2048m', '--classifier', self.fp], stdout=PIPE)
		
		cur_class = None
		
		#=======================================================================
		# Process the output features
		#=======================================================================
		for line in p.stdout:
			
			line = line.decode('utf-8')
			
			#===================================================================
			# When the line contains a new class, change the state to that
			#===================================================================
			
			if line.startswith('FEATURES FOR'):
				cur_class = line[19:].strip()
				continue
			
			#===================================================================
			# Otherwise, process the feature weights
			#===================================================================
			
			else:
				feat, score = re.split('\s+', line.strip())
				score = float(score)
				self.feats[cur_class][feat] += score
		
		#=======================================================================
		# Now, print out the top N weights (and bottom N)
		#=======================================================================
				
		for i, key in enumerate(self.feats.keys()):
			print(key,end='\n')
			feats = self.feats[key]
			default_feat = feats['<default>']
			print('<default> %s' % (default_feat))
			del feats['<default>']
			
			#===================================================================
			# Sort by either best or worst feats
			#===================================================================
			feat_items = sorted(feats.items(), key=lambda feat: feat[1], reverse=True)
			
			for feat, score in feat_items[:10]:
				print(feat, score)
			
			print()
		
				
		
			
			
			
		
		
		
		
		