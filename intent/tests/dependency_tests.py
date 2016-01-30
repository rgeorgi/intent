import os
from unittest.case import TestCase

from intent.igt.igt_functions import project_ds_tier, get_lang_ds
from intent.igt.parsing import xc_load
from xigt.codecs import xigtxml
from intent.utils.env import testfile_dir

dep_file = os.path.join(testfile_dir, 'xigt/dependency_tests.xml')

class MissingCoNLLTokenTest(TestCase):
    def setUp(self):

        self.xc = xc_load(dep_file)
        self.inst = self.xc[3]

    def all_tokens_present_test(self):
        project_ds_tier(self.inst)
        ds = get_lang_ds(self.inst)
        print(ds.to_conll())


