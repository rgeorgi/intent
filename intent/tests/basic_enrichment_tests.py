import os
from unittest import TestCase
from intent.igt.igtutils import rgp
from intent.igt.rgxigt import RGCorpus, NoODINRawException, morph_align, word_align
from intent.utils.env import proj_root, testfile_dir

__author__ = 'rgeorgi'

class NoRawTest(TestCase):
    def setUp(self):
        self.xc = RGCorpus.load(os.path.join(testfile_dir, 'xigt/no_raw.xml'))

    def no_raw_test(self):
        """
        There is no raw tier in this instance, so it should return a failure.
        """
        self.assertRaises(NoODINRawException, self.xc[0].raw_tier)

    def clean_test(self):
        """
        The "clean" tier is already defined in this example. Assert that it is simply
        returned without incident.
        """
        self.assertIsNotNone(self.xc[0].clean_tier())

    def norm_test(self):
        """
        Ensure that the normal tier is created without incident.
        """
        self.assertIsNotNone(self.xc[0].normal_tier())

    def gloss_test(self):
        """
        Ensure that the gloss gets created, and that it doesn't
        get created twice by accident.
        """
        self.assertIsNotNone(self.xc[0].gloss)
        self.assertIsNotNone(self.xc[0].gloss)

    def trans_test(self):
        self.assertIsNotNone(self.xc[0].trans)
        self.assertIsNotNone(self.xc[0].trans)

    def lang_test(self):
        self.assertIsNotNone(self.xc[0].trans)
        self.assertIsNotNone(self.xc[0].trans)

    def glosses_test(self):
        self.assertIsNotNone(self.xc[0].glosses)
        self.assertIsNotNone(self.xc[0].glosses)

    def morphs_test(self):
        self.assertIsNotNone(self.xc[0].morphemes)
        self.assertIsNotNone(self.xc[0].morphemes)

    def morph_align_test(self):
        morph_align(self.xc[0].glosses, self.xc[0].morphemes)

    def word_align_test(self):
        word_align(self.xc[0].gloss, self.xc[0].lang)
