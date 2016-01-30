import copy
from unittest import TestCase

from intent.alignment.Alignment import heur_alignments, Alignment
from intent.igt.igt_functions import heur_align_inst, tier_tokens, classify_gloss_pos, tag_trans_pos
from intent.igt.parsing import raw_txt_to_inst, create_words_tier_from_string
from intent.utils.token import tokenize_string


class heur_tests(TestCase):

    def setUp(self):
        self.inst = raw_txt_to_inst("balhd       dfds dkkdf ldf\n" +
                                    "experiment  this is      a\n" +
                                    "this        is    a      test")

        self.gloss_tokens = tokenize_string("experiment  this is      a")
        self.trans_tokens = tokenize_string("this        is    a      test")

        self.a = Alignment([(2,3),(1,2),(3,4)])
        self.a2 = Alignment([(2,3),(1,2),(3,4),(4,1)])


    def test_inst_heur(self):
        h = heur_align_inst(self.inst)
        self.assertEqual(self.a, h)

    def test_direct_heur(self):

        h = heur_alignments(self.gloss_tokens, self.trans_tokens).flip()
        self.assertEqual(self.a, h)

    def test_direct_pos_heur(self):
        gloss_pos = tier_tokens(create_words_tier_from_string('NOUN PRON VERB DET'))
        trans_pos = tier_tokens(create_words_tier_from_string('NOUN VERB DET NOUN'))

        h = heur_alignments(self.gloss_tokens, self.trans_tokens, gloss_pos=gloss_pos, trans_pos=trans_pos).flip()
        self.assertEqual(self.a2, h)

    def test_inst_pos_heur(self):
        inst = copy.deepcopy(self.inst)
        print(classify_gloss_pos(inst))
        print(tag_trans_pos(inst))
        print(heur_align_inst(inst, use_pos=True))


