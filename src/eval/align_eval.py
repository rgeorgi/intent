'''
Created on Feb 14, 2014

@author: rgeorgi
'''
import sys

class AlignEval():
	def __init__(self, aligned_corpus_a, aligned_corpus_b, debug = False, filter=None):
		self.matches = 0.
		self.total_test = 0.
		self.total_gold = 0.
		self._instances = 0
		
		aligned_corpus = zip(aligned_corpus_a, aligned_corpus_b)
		self._parallel = list(aligned_corpus)		

		for model_sent, gold_sent in self._parallel:
	
			model_aln = model_sent.aln
			gold_aln = gold_sent.aln
			
			# So we can filter by lang
			if filter and filter[0] in model_sent.attrs and model_sent.attrs[filter[0]] != filter[1]:
				continue
			
			self._instances += 1
			
			# Only look for alignments which are non-null...
			model_aln = set([(src,tgt) for src,tgt in model_aln if src > 0 and tgt > 0])
			gold_aln = set([(src,tgt) for src,tgt in gold_aln if src > 0 and tgt > 0])
			#  -----------------------------------------------------------------------------
			
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
		return 1.0 - 2*self.matches/(self.total_test + self.total_gold)
	
	def precision(self):
		return self.matches / self.total_test
	
	def recall(self):
		return self.matches / self.total_gold
		
	@property
	def instances(self):
		return self._instances
		
	def fmeasure(self):
		return 2*(self.precision()*self.recall())/(self.precision()+self.recall())
	
	def all(self):
		return '%f,%f,%f,%f' % (self.aer(), self.precision(), self.recall(), self.fmeasure())

		