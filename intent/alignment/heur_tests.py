from unittest import TestCase

from intent.alignment.Alignment import heur_alignments, Alignment
from intent.igt.igtutils import rgp
from intent.igt.rgxigt import RGWordTier, RGIgt
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.utils.env import classifier, tagger_model
from intent.utils.token import tokenize_string


class heur_tests(TestCase):

    def setUp(self):
        self.inst = RGIgt.fromRawText("balhd       dfds dkkdf ldf\n" +
                                      "experiment  this is      a\n" +
                                      "this        is    a      test")

        self.gloss_tokens = tokenize_string("experiment  this is      a")
        self.trans_tokens = tokenize_string("this        is    a      test")

        self.a = Alignment([(2,3),(1,2),(3,4)])
        self.a2 = Alignment([(2,3),(1,2),(3,4),(4,1)])


    def test_inst_heur(self):
        h = self.inst.heur_align()
        self.assertEqual(self.a, h)

    def test_direct_heur(self):

        h = heur_alignments(self.gloss_tokens, self.trans_tokens).flip()
        self.assertEqual(self.a, h)

    def test_direct_pos_heur(self):
        gloss_pos = RGWordTier.from_string('NOUN PRON VERB DET').tokens()
        trans_pos = RGWordTier.from_string('NOUN VERB DET NOUN').tokens()

        h = heur_alignments(self.gloss_tokens, self.trans_tokens, gloss_pos=gloss_pos, trans_pos=trans_pos).flip()
        self.assertEqual(self.a2, h)

    def test_inst_pos_heur(self):
        inst = self.inst.copy()
        print(inst.classify_gloss_pos(MalletMaxent(classifier)))
        print(inst.tag_trans_pos(StanfordPOSTagger(tagger_model)))
        print(inst.heur_align(use_pos=True))


