'''
Created on Feb 14, 2014

@author: rgeorgi
'''
import sys
from intent.alignment.Alignment import MorphAlign, Alignment

class AlignEval():
    def __init__(self, test_alignments=None, gold_alignments=None, debug = False, filter=None, reverse=False, explicit_nulls = False):
        """
        :param test_alignments:
         :type test_alignments: list[Alignment]
        :param gold_alignments:
        :type gold_alignments: list[Alignment]
        :param debug:
        :param filter:
        :param reverse:
        :param explicit_nulls:
        """
        self.matches = 0.
        self.total_test = 0.
        self.total_gold = 0.
        self._instances = 0

        self.prob_matches = 0
        self.sure_matches = 0

        self.total_prob = 0
        self.total_sure = 0

        if test_alignments is None:
            test_alignments = []
        if gold_alignments is None:
            gold_alignments = []

        assert len(test_alignments) == len(gold_alignments), '{} vs. {}'.format(len(test_alignments), len(gold_alignments))

        for model_aln, gold_aln in zip(test_alignments, gold_alignments):

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
            prob_gold_aln  = Alignment([a for a in gold_aln if a.type == 'p'])
            sure_gold_aln  = Alignment([a for a in gold_aln if a.type == 's'])

            self.prob_matches += len(model_aln & prob_gold_aln)
            self.sure_matches += len(model_aln & sure_gold_aln)

            self.total_prob += len(prob_gold_aln)
            self.total_sure += len(sure_gold_aln)

            self.matches += len(model_aln & gold_aln)
            self.total_test += len(model_aln)
            self.total_gold += len(gold_aln)

    def aer(self, p_s = False):
        '''
        Return the Alignment Error Rate (AER).
        '''
        if not p_s:
            if not self.total_gold:
                return 0
            else:
                return 1.0 - 2*self.matches/(self.total_test + self.total_gold)
        else:
            if not (self.total_prob + self.total_sure):
                return 0
            else:
                return 1.0 - (self.sure_matches+self.prob_matches) / (self.total_test+self.total_gold)


    def precision(self, p_s = None):
        if not self.total_test:
            return 0
        elif p_s is None:
            return self.matches / self.total_test
        elif p_s is 'p':
            return self.prob_matches / self.total_test
        elif p_s is 's':
            return self.sure_matches / self.total_test
        else:
            raise NotImplementedError

    def recall(self, p_s = None):
        if not self.total_gold:
            return 0
        elif p_s is None:
            return self.matches / self.total_gold
        elif p_s is 'p':
            return self.prob_matches / self.total_prob
        elif p_s is 's':
            return self.sure_matches / self.total_sure
        else:
            raise NotImplementedError


    @property
    def instances(self):
        return self._instances

    def fmeasure(self, p_s = None):
        try:
            return 2*(self.precision(p_s)*self.recall(p_s))/(self.precision(p_s)+self.recall(p_s))
        except ZeroDivisionError:
            return 0

    @classmethod
    def header(cls):
        return '{},{},{},{},{},{},{}'.format('aer','precision','recall', 'fmeasure','matches','total_gold','total_test')

    def all(self, p_s=False):
        return (self.aer(p_s), self.precision(), self.recall(), self.fmeasure(), self.matches, self.total_gold, self.total_test)

    def all_str(self):
        return '%f,%f,%f,%f,%d,%d,%d' % self.all()

    def __add__(self, other):
        assert isinstance(other, AlignEval)

        retae = AlignEval()
        retae._instances = self._instances + other._instances
        retae.matches = self.matches + other.matches
        retae.total_gold = self.total_gold + other.total_gold
        retae.total_test = self.total_test + other.total_test

        return retae
