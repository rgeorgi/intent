'''
Created on Feb 14, 2014

@author: rgeorgi
'''
import sys
from intent.alignment.Alignment import MorphAlign, Alignment

class AlignEval():
	def __init__(self, aligned_corpus_a, aligned_corpus_b, debug = False, filter=None, reverse=False, explicit_nulls = False):
		self.matches = 0.
		self.total_test = 0.
		self.total_gold = 0.
		self._instances = 0
		
		aligned_corpus = zip(aligned_corpus_a, aligned_corpus_b)
		self._parallel = list(aligned_corpus)		
		
		for model_sent, gold_sent in self._parallel:
			
			
			model_aln = model_sent.aln
			gold_aln = gold_sent.aln
			
			# If we are going to count the lack of an alignment
			# as an explicit null...
			if explicit_nulls:
				model_aln = model_sent.aln_with_nulls()
				gold_aln = gold_sent.aln_with_nulls()
				
			# So we can filter by lang
			if filter and filter[0] in model_sent.attrs and model_sent.attrs[filter[0]] != filter[1]:
				continue
			
			self._instances += 1
			
			
			if reverse:
				model_aln = model_aln.flip()
			
			
			#model_aln = model_aln.nonzeros()
			#gold_aln = gold_aln.nonzeros()
			#  -----------------------------------------------------------------------------
			
			#===================================================================
			# If we're dealing with morph alignments in the gold...
			#===================================================================
			
			if isinstance(gold_aln, MorphAlign):
				# Remap the model alignment to use the 
				# gloss indices found in the gold alignment.
				model_aln = gold_aln.remap(model_aln)
				
				gold_aln = gold_aln.GlossAlign
				
			
			matches = model_aln & gold_aln
			
			# For debugging, let's look where we messed up.
			incorrect_alignments = model_aln - matches
			missed_alignments = gold_aln - model_aln
			
			#===================================================================
			# Debugging to show where we are missing alignments. 
			#===================================================================
			
			if debug:
				if incorrect_alignments or missed_alignments:
					sys.stderr.write('-'*80+'\n')
					sys.stderr.write(model_sent.get_attr('file')+' --- '+str(model_sent.get_attr('id'))+'\n')
						
				if incorrect_alignments:
					sys.stderr.write('INCORRECT ALIGNMENTS: ')
					sys.stderr.write(str(model_sent.wordpairs(incorrect_alignments))+'\n')
				
				if missed_alignments:
					sys.stderr.write('MISSED ALIGNMENTS: ')
					sys.stderr.write(str(model_sent.wordpairs(missed_alignments))+'\n')
						
			self.matches += len(model_aln & gold_aln)
			self.total_test += len(model_aln)
			self.total_gold += len(gold_aln)

			
	def aer(self):
		'''
		Return the Average Error Rate (AER). 
		'''
		if not self.total_gold:
			return 0
		else:
			return 1.0 - 2*self.matches/(self.total_test + self.total_gold)
	
	def precision(self):
		if not self.total_test:
			return 0
		else:
			return self.matches / self.total_test
	
	def recall(self):
		try:
			return self.matches / self.total_gold
		except ZeroDivisionError:
			return 0
		
	@property
	def instances(self):
		return self._instances
		
	def fmeasure(self):
		try:
			return 2*(self.precision()*self.recall())/(self.precision()+self.recall())
		except ZeroDivisionError:
			return 0
	
	def all(self):
		return '%f,%f,%f,%f,%d,%d,%d' % (self.aer(), self.precision(), self.recall(), self.fmeasure(), self.matches, self.total_gold, self.total_test)

		