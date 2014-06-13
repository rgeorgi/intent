'''
Created on Apr 4, 2014

@author: rgeorgi
'''
import os
from utils.ConfigFile import ConfigFile
import subprocess as sub
import sys
from classify.Classification import Classification
from utils.TwoLevelCountDict import TwoLevelCountDict
import re

class MalletTool(object):

	def __init__(self):	
		mydir = os.path.abspath(os.path.dirname(__file__))
		c = ConfigFile(os.path.join(mydir, 'mallet.prop'))
		
		self.mallet = c['mallet']