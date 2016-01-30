import os
from unittest import TestCase

from intent.igt.igt_functions import classify_gloss_pos
from intent.igt.parsing import xc_load
from intent.utils.env import testfile_dir


__author__ = 'rgeorgi'

class ClassificationTests(TestCase):

    def broken_german_test(self):

        xc = xc_load(os.path.join(testfile_dir, 'xigt/broken-german-instance.xml'))
        inst = xc[0]
        self.assertIsNotNone(classify_gloss_pos(inst))
