'''
Created on Mar 6, 2014

@author: rgeorgi
'''
import os
import codecs
import chardet

class POSCorpus(list):
	'''
	POS Tag corpus object to attempt to unify inputs and outputs.
	'''
	
	def __init__(self, seq = []):
		list.__init__(self, seq)
		
	def add(self, inst):
		if not isinstance(inst, POSCorpusInstance):
			raise POSCorpusException('Attempt to add non-POSCorpusInstance to POSCorpus')
		else:
			list.append(self, inst)
			
	def slashtags(self, delimeter = '/', lowercase=True):
		'''
		Return the corpus in slashtags ( John/NN Stewart/NN ) format.
		
		@param delimeter:
		@param lowercase:
		'''
		ret_str = ''
		for inst in self:
			ret_str += inst.slashtags(delimeter=delimeter, lowercase=lowercase)+'\n'
		return ret_str
			
	def raw(self):
		ret_str = ''
		for inst in self:
			ret_str += inst.raw()+'\n'
		return ret_str
			
	def matches(self, other):
		if not isinstance(other, POSCorpus):
			raise POSCorpusException('Attempting to compare non-POSCorpus with POSCorpus')
		if len(self) != len(other):
			raise POSCorpusException('Attempt to compare POSCorpus instances of different length')
		
		zipped = zip(self, other)
		matches = 0
		for myself, other in zipped:
			matches += myself.matches(other)
		return matches
	
	def tokens(self):
		tokens = []
		for inst in self:
			tokens.extend(inst)
		return tokens
	
	def accuracy(self, other):
		return self.matches(other) / float(len(self.tokens()))
			
	def mallet(self, lowercase=True):
		ret_str = ''
		for inst in self:
			ret_str += inst.mallet(lowercase=lowercase)+'\n'
		return ret_str
			
	def split(self, percent = 100.):
		index = int(round((percent/100.)*len(self)))
		train = POSCorpus(self[:index])
		test = POSCorpus(self[index:])
		return train, test
	
	def write(self, path, format, delimeter = '/', outdir = os.getcwd(), lowercase = True):

		path = os.path.join(outdir, path)
		
		if path and len(self):
			f = codecs.open(path, 'w', encoding='utf-8')
			if format == 'mallet':
				f.write(self.mallet(lowercase=lowercase))
			elif format == 'slashtags':
				f.write(self.slashtags(delimeter=delimeter, lowercase=lowercase))
			elif format == 'raw':
				f.write(self.raw())
			else:
				raise POSCorpusException('Unknown output format requested.')
			f.close()
			
	def writesplit(self, train_path, test_path, split, format, delimeter = '/', outdir = os.getcwd(), lowercase=True):
		train, test = self.split(split)
		if train_path and len(train):
			train.write(train_path, format, delimeter, outdir, lowercase)
		if test_path and len(test):
			test.write(test_path, format, delimeter, outdir, lowercase)

	
class POSToken:
	def __init__(self, form, label = None):
				
		self.form = form
		self.label = label
			
class POSCorpusException(Exception):
	def __init__(self, msg = None):
		Exception.__init__(self, msg)
		

class POSCorpusInstance(list):
	def __init__(self, seq=[], id_ref=None):
		self.id_ref = id_ref
		list.__init__(self, seq)
		
	def matches(self, other):
		if not isinstance(other, POSCorpusInstance):
			raise POSCorpusException('Attempting to compare non-POSCorpusInstance to POSCorpusInstance')
		if len(self) != len(other):
			raise POSCorpusException('Mismatched length in POSCorpus compare')
		
		zipped = zip(self, other)
		
		count = 0
		
		for my_token, o_token in zipped:
			if my_token.label == o_token.label:
				count+=1
		return count
			
	def append(self, token):
		if not isinstance(token, POSToken):
			raise POSCorpusException('Attempting to add non-token to POSCorpusInstance')
		else:
			list.append(self, token)
			
	def __str__(self):
		return '<POSCorpusInstance: %s>' % self.slashtags()
			
	def raw(self, lowercase=True):
		ret_str = ''
		for token in self:
			form = token.form
			if lowercase:
				form = form.lower()
			ret_str += form+' '
		return ret_str.strip()
	
	def slashtags(self, delimeter = '/', lowercase=True):
		ret_str = ''
		for token in self:
			form = token.form
			if lowercase:
				form = token.form.lower()
			ret_str += '%s/%s ' % (form, token.label)
		return ret_str.strip()
	
	def mallet(self, lowercase=True):
		ret_str = ''
		for token in self:
			form = token.form
			if lowercase:
				form = token.form.lower()
			ret_str += '%s %s\n' % (form, token.label)
		return ret_str
				
		