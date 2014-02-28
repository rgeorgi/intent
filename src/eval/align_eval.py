'''
Created on Feb 14, 2014

@author: rgeorgi
'''



class AlignEval():
	def __init__(self, aligned_corpus_a, aligned_corpus_b):
		self.matches = 0.
		self.total_test = 0.
		self.total_gold = 0.
		
		aligned_corpus = zip(aligned_corpus_a, aligned_corpus_b)

		for model_sent, gold_sent in aligned_corpus:
			model_aln = model_sent.aln
			gold_aln = gold_sent.aln
		
		
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


def aer(aligned_corpus):
	
	numerator = 0.
	denominator = 0.
	
	for model_sent, gold_sent in aligned_corpus:
		model_aln = model_sent.alignment
		gold_aln = gold_sent.alignment
		
		numerator += float(2*len(model_aln& gold_aln))
		denominator += float(len(model_aln) + len(gold_aln))
		
	return 1.0 - numerator / denominator
