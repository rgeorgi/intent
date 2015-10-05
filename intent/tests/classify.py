import os
from unittest import TestCase
from intent.igt.rgxigt import RGCorpus
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.utils.env import classifier, testfile_dir


__author__ = 'rgeorgi'

class ClassificationTests(TestCase):

    def broken_german_test(self):

        xc = RGCorpus.load(os.path.join(testfile_dir, 'xigt/broken-german-instance.xml'))
        inst = xc[0]
        self.assertIsNotNone(inst.classify_gloss_pos(MalletMaxent(classifier)))