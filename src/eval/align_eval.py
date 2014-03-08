'''
Created on Feb 14, 2014

@author: rgeorgi
'''
import sys

class AlignEval():
	def __init__(self, aligned_corpus_a, aligned_corpus_b, debug = True):
		self.matches = 0.
		self.total_test = 0.
		self.total_gold = 0.
		
		aligned_corpus = zip(aligned_corpus_a, aligned_corpus_b)
		self._parallel = list(aligned_corpus)		

		for model_sent, gold_sent in self._parallel:
	
			model_aln = model_sent.aln
			gold_aln = gold_sent.aln
			
			matches = model_aln & gold_aln
			
			# For debugging, let's look where we messed up.
			incorrect_alignments = model_aln - matches
			missed_alignments = gold_aln - model_aln
			
			#===================================================================
			# Debugging to show where we are missing alignments. 
			#===================================================================
			
			if debug:				
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
		return 1.0 - 2*self.matches/(self.total_test + self.total_gold)
	
	def precision(self):
		return self.matches / self.total_test
	
	def recall(self):
		return self.matches / self.total_gold
	
	def fmeasure(self):
		return 2*(self.precision()*self.recall())/(self.precision()+self.recall())
	
	def all(self):
		return '%f,%f,%f,%f' % (self.aer(), self.precision(), self.recall(), self.fmeasure())

		