import os
from unittest.case import TestCase

from intent.igt.rgxigt import RGCorpus
from xigt.codecs import xigtxml
from intent.utils.env import testfile_dir

dep_file = os.path.join(testfile_dir, 'xigt/dependency_tests.xml')

class MissingCoNLLTokenTest(TestCase):
    def setUp(self):

        self.xc = RGCorpus.load(dep_file)
        self.inst = self.xc[3]

    def all_tokens_present_test(self):
        self.inst.project_ds()
        ds = self.inst.get_lang_ds()
        print(ds.to_conll())


