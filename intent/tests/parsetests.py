import logging
import os
from unittest import TestCase
from intent.igt import rgxigt
from intent.igt.consts import DS_TIER_TYPE
from intent.igt.igtutils import rgp
from intent.igt.rgxigt import RGXigtException, RGCorpus, read_ds
from intent.subcommands import enrich
from intent.trees import DepTree
from intent.utils.env import proj_root, testfile_dir

__author__ = 'rgeorgi'


ctn_file = os.path.join(testfile_dir, 'ctn2-xigt.xml')
ger_file = os.path.join(testfile_dir, 'single_ger.xml')
kor_file = os.path.join(testfile_dir, 'kor-ex.xml')

xigt_proj = os.path.join(testfile_dir, 'xigt-projection-tests.xml')

no_enrich_args = {'OUT_FILE':'/dev/null'}

class ParseTests(TestCase):

    def test_ctn(self):
        enrich(IN_FILE=ctn_file, **no_enrich_args)

    def test_kor(self):
        enrich(IN_FILE=kor_file, **no_enrich_args)

    def test_ger(self):
        enrich(IN_FILE=ger_file, **no_enrich_args)

class ReadTreeTests(TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.xc = RGCorpus.load(xigt_proj, basic_processing=True)
        self.inst = self.xc[0]

    def test_read_ds_tree(self):
        ds_tier = self.inst.get_trans_ds()
        ds = read_ds(ds_tier)
        r = DepTree.from_ptbstring("""
(ROOT[0] (found[2] (Someone[1]) (them[3]) (boring.[4])))""")

        self.assertTrue(r.structurally_eq(ds))

    def test_project_ds_tree(self):
        self.inst.project_ds()
        

