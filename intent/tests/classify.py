from unittest import TestCase
import sys
from intent.igt.grams import write_gram
from intent.igt.igtutils import rgp
from intent.igt.rgxigt import RGCorpus
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.utils.env import classifier
from intent.utils.token import POSToken, GoldTagPOSToken

__author__ = 'rgeorgi'

class ClassificationTests(TestCase):

    def broken_german_test(self):
        xc = RGCorpus.load('./examples/tests/broken-german-instance.xml')
        inst = xc[0]
        self.assertIsNotNone(inst.classify_gloss_pos(MalletMaxent(classifier)))