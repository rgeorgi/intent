"""
Created on Feb 24, 2015

:author: rgeorgi <rgeorgi@uw.edu>
"""
import copy
import os
from unittest import TestCase

from intent.alignment.Alignment import Alignment
from intent.consts import INTENT_ALN_HEUR, INTENT_ALN_GIZA, INTENT_POS_PROJ, INTENT_ALN_MANUAL
from intent.igt.create_tiers import lang, glosses, gloss, trans
from intent.igt.references import xigt_find, item_index
from intent.igt.rgxigt import RGCorpus, RGIgt
from intent.igt.igt_functions import pos_tags, project_gloss_pos_to_lang, giza_align_t_g, heur_align_inst, \
    heur_align_corp, add_pos_tags, tier_tokens, classify_gloss_pos, tag_trans_pos, tier_text, set_bilingual_alignment, \
    get_trans_glosses_alignment
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.utils.env import posdict, classifier, tagger_model, testfile_dir

xc = RGCorpus.load(os.path.join(testfile_dir, "xigt/kor-ex.xml"))

class GlossAlignTest(TestCase):

    def test_gloss_projection_unaligned(self):
        xc = RGCorpus.load(os.path.join(testfile_dir, "xigt/project_gloss_lang_tests.xml"))
        igt = xc[0]
        project_gloss_pos_to_lang(igt, tag_method=INTENT_POS_PROJ, unk_handling='keep')
        self.assertEqual('UNK', pos_tags(igt, lang(igt).id, INTENT_POS_PROJ)[-1].value())



#===============================================================================
# Unit Tests
#===============================================================================


class TextParseTest(TestCase):

    def setUp(self):
        self.txt = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''

        self.igt = RGIgt.fromString(self.txt)


    def line_test(self):
        """
        Test that lines are rendered correctly.
        """
        self.assertEqual(tier_text(gloss(self.igt)), 'I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec')
        self.assertEqual(tier_text(trans(self.igt)), 'I made the child eat rice')

    def glosses_test(self):
        """
        Test that the glosses are rendered correctly.
        """
        self.assertEqual(len(glosses(self.igt)), 10)
        self.assertEqual(tier_text(glosses(self.igt)), 'I Nom child Dat rice Acc eat Caus Pst Dec')

    def word_align_test(self):
        """
        Test that the gloss has been automatically aligned at the word level correctly.
        """
        at = Alignment()
        for gw in gloss(self.igt):
            gw_idx = item_index(gw)
            lw = xigt_find(self.igt, id=gw.alignment)
            if lw is not None:
                at.add((gw_idx, item_index(lw)))


        self.assertEqual(at, Alignment([(1,1),(2,2),(3,3),(4,4)]))


    def set_bilingual_align_test(self):
        """
        Set the bilingual alignment manually, and ensure that it is read back correctly.
        """

        a = Alignment([(1,1),(1,2),(2,8),(4,3),(5,7),(6,5)])
        set_bilingual_alignment(self.igt, trans(self.igt), glosses(self.igt), a, INTENT_ALN_MANUAL)
        get_trans_glosses_alignment(self.igt, INTENT_ALN_MANUAL)

class XigtParseTest(TestCase):
    """
    Testcase to make sure we can load from XIGT objects.
    """
    def setUp(self):
        self.xc = RGCorpus.load(os.path.join(testfile_dir, 'xigt/kor-ex.xml'))

    def xigt_load_test(self):
        pass

    def giza_align_test(self):
        new_c = copy.deepcopy(self.xc)
        giza_align_t_g(new_c)
        giza_aln = new_c[0].get_trans_glosses_alignment(aln_method=INTENT_ALN_GIZA)

        self.assertIsNotNone(giza_aln)

    def heur_align_test(self):
        new_c = copy.deepcopy(self.xc)
        heur_align_corp(xc)
        aln = new_c[0].get_trans_glosses_alignment(aln_method=INTENT_ALN_HEUR)
        a = Alignment([(5, 7), (6, 5), (1, 1), (4, 3)])
        self.assertEquals(a, aln)


class POSTestCase(TestCase):

    def setUp(self):
        self.txt = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''
        self.igt = RGIgt.fromString(self.txt)
        self.tags = ['PRON', 'NOUN', 'NOUN', 'VERB']

    def test_add_pos_tags(self):
        add_pos_tags(self.igt, 'gw', self.tags)

        self.assertEquals(tier_tokens(pos_tags(self.igt, 'gw')), self.tags)

    def test_classify_pos_tags(self):
        tags = classify_gloss_pos(self.igt, MalletMaxent(), posdict=posdict)
        self.assertEqual(tags, self.tags)


    def test_tag_trans_line(self):
        tagger = StanfordPOSTagger(tagger_model)
        tag_trans_pos(self.igt)


