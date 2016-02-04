import os
from unittest import TestCase

from intent.igt.create_tiers import morphemes, get_raw_tier, generate_normal_tier, generate_clean_tier
from intent.igt.parsing import xc_load
from intent.igt.references import cleaned_tier, normalized_tier
from xigt.codecs import xigtxml

from intent.utils.env import proj_root, testfile_dir

__author__ = 'rgeorgi'

class NoRawTest(TestCase):
    def setUp(self):
        self.xc = xc_load(os.path.join(testfile_dir, 'xigt/no_raw.xml'))

    def no_raw_test(self):
        """
        There is no raw tier in this instance, so it should return a failure.
        """
        self.assertRaises(NoODINRawException, get_raw_tier, self.xc[0])

    def clean_test(self):
        """
        The "clean" tier is already defined in this example. Assert that it is simply
        returned without incident.
        """
        self.assertIsNotNone(generate_clean_tier(self.xc[0]))

    def norm_test(self):
        """
        Ensure that the normal tier is created without incident.
        """
        self.assertIsNotNone(generate_normal_tier(self.xc[0]))

    def gloss_test(self):
        """
        Ensure that the gloss gets created, and that it doesn't
        get created twice by accident.
        """
        self.assertIsNotNone(gloss(self.xc[0]))
        self.assertIsNotNone(gloss(self.xc[0]))

    def trans_test(self):
        self.assertIsNotNone(trans(self.xc[0]))
        self.assertIsNotNone(trans(self.xc[0]))

    def lang_test(self):
        self.assertIsNotNone(lang(self.xc[0]))
        self.assertIsNotNone(lang(self.xc[0]))

    def glosses_test(self):
        self.assertIsNotNone(glosses(self.xc[0]))
        self.assertIsNotNone(glosses(self.xc[0]))

    def morphs_test(self):
        self.assertIsNotNone(morphemes(self.xc[0]))
        self.assertIsNotNone(morphemes(self.xc[0]))

    def morph_align_test(self):
        morph_align(glosses(self.xc[0]), morphemes(self.xc[0]))

    def word_align_test(self):
        word_align(gloss(self.xc[0]), lang(self.xc[0]))

class NullGlossTest(TestCase):

    def setUp(self):
        self.path = os.path.join(testfile_dir, 'xigt/deu_no_gloss_line.xml')

    def test_basic_processing(self):
        xc = xc_load(self.path, do_basic_processing=True)

class L_G_WordAlignTests(TestCase):

    def setUp(self):
        path = os.path.join(testfile_dir, 'xigt/multiple_line_tests.xml')
        with open(path, 'r', encoding='utf-8') as f:
            self.xc = xigtxml.load(f)

    def align_test(self):
        """
        Confirm that the question mark gets split and is its own token,
        but also that the lang and gloss lines still align correctly.
        """
        inst = self.xc[1]
        self.assertEqual(len(lang(inst)), 4)
        self.assertEqual(len(gloss(inst)), 3)
        self.assertIsNone(word_align(gloss(inst), lang(inst)))

    def test_correct_multiple_lang_behavior(self):
        inst = self.xc[0]
        inst2 = self.xc[1]
        self.assertRaises(GlossLangAlignException, word_align, gloss(inst), lang(inst))
        self.assertIsNone(word_align(gloss(inst2), lang(inst2)))

from intent.igt.igt_functions import *