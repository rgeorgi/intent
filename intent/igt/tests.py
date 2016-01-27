"""
Created on Feb 24, 2015

:author: rgeorgi <rgeorgi@uw.edu>
"""
import os
from unittest import TestCase

from intent.alignment.Alignment import Alignment
from intent.consts import INTENT_ALN_HEUR, INTENT_ALN_GIZA, INTENT_POS_PROJ
from intent.igt.rgxigt import RGCorpus, RGIgt
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.utils.env import posdict, classifier, tagger_model, testfile_dir

xc = RGCorpus.load(os.path.join(testfile_dir, "xigt/kor-ex.xml"))

class GlossAlignTest(TestCase):

    def test_gloss_projection_unaligned(self):
        xc = RGCorpus.load(os.path.join(testfile_dir, "xigt/project_gloss_lang_tests.xml"))
        igt = xc[0]
        igt.project_gloss_to_lang(tag_method=INTENT_POS_PROJ, unk_handling='keep')

        self.assertEqual('UNK', igt.get_pos_tags(igt.lang.id, INTENT_POS_PROJ)[-1].value())



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
        self.assertEqual(self.igt.gloss.text(), 'I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec')
        self.assertEqual(self.igt.trans.text(), 'I made the child eat rice')

    def glosses_test(self):
        """
        Test that the glosses are rendered correctly.
        """
        self.assertEqual(len(self.igt.glosses), 10)
        self.assertEqual(self.igt.glosses.text(), 'I Nom child Dat rice Acc eat Caus Pst Dec')

    def word_align_test(self):
        """
        Test that the gloss has been automatically aligned at the word level correctly.
        """
        at = self.igt.gloss.get_aligned_tokens()

        self.assertEqual(at, Alignment([(1,1),(2,2),(3,3),(4,4)]))

    def set_align_test(self):
        """
        Check setting alignment attributes between tiers.
        """
        self.igt.gloss.set_aligned_tokens(self.igt.lang, Alignment([(1,1),(2,2)]))
        self.assertEqual(self.igt.gloss.get_aligned_tokens(), Alignment([(1,1),(2,2)]))

    def set_bilingual_align_test(self):
        """
        Set the bilingual alignment manually, and ensure that it is read back correctly.
        """

        a = Alignment([(1,1),(1,2),(2,8),(4,3),(5,7),(6,5)])
        self.igt.set_bilingual_alignment(self.igt.trans, self.igt.glosses, a, 'manual')

        self.assertEqual(a, self.igt.get_trans_glosses_alignment())

class XigtParseTest(TestCase):
    """
    Testcase to make sure we can load from XIGT objects.
    """
    def setUp(self):
        self.xc = RGCorpus.load(os.path.join(testfile_dir, 'xigt/kor-ex.xml'))

    def xigt_load_test(self):
        pass

    def giza_align_test(self):
        new_c = self.xc.copy()
        new_c.giza_align_t_g()
        giza_aln = new_c[0].get_trans_glosses_alignment(aln_method=INTENT_ALN_GIZA)

        self.assertIsNotNone(giza_aln)

    def heur_align_test(self):
        new_c = self.xc.copy()
        new_c.heur_align()
        aln = new_c[0].get_trans_glosses_alignment(aln_method=INTENT_ALN_HEUR)
        a = Alignment([(5, 7), (6, 5), (1, 1), (4, 3)])
        self.assertEquals(a, aln)

class CopyTest(TestCase):
        def setUp(self):
            self.txt = '''doc_id=38 275 277 L G T
                            stage3_lang_chosen: korean (kor)
                            lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
                            note: lang_chosen_idx=0
                            line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
                            line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
                            line=961 tag=T:     `I made the child eat rice.\''''
            self.igt = RGIgt.fromString(self.txt)
            self.corpus = RGCorpus(igts=[self.igt])

        def test_copy(self):

            new_c = self.corpus.copy()

            self.assertNotEqual(id(self.corpus), id(new_c))

            # Assert that there is no alignment.
            self.assertIsNone(self.corpus.find(type='bilingual-alignments'))

            new_c.heur_align()
            self.assertIsNotNone(new_c.find(type='bilingual-alignments'))
            self.assertIsNone(self.corpus.find(id='bilingual-alignments'))

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

        self.igt.add_pos_tags('gw', self.tags)

        self.assertEquals(self.igt.get_pos_tags('gw').tokens(), self.tags)

    def test_classify_pos_tags(self):
        tags = self.igt.classify_gloss_pos(MalletMaxent(classifier), posdict=posdict)

        self.assertEqual(tags, self.tags)


    def test_tag_trans_line(self):
        tagger = StanfordPOSTagger(tagger_model)
        self.igt.tag_trans_pos(tagger)

