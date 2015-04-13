import os
from unittest import TestCase
from intent.subcommands import enrich
from intent.utils.env import proj_root

__author__ = 'rgeorgi'

example_dir = os.path.join(proj_root, './examples')

ctn_file = os.path.join(example_dir, 'ctn2-xigt.xml')
ger_file = os.path.join(example_dir, 'single_ger.xml')
kor_file = os.path.join(example_dir, 'kor-ex.xml')

no_enrich_args = {'OUT_FILE':'/dev/null',
                  'pos_trans':0,
                  'pos_lang':'none',
                  'alignment':'none',
                  'parse_trans':0,
                  'project_pt':0}

class ParseTests(TestCase):

    def test_ctn(self):
        enrich(IN_FILE=ctn_file, **no_enrich_args)

    def test_kor(self):
        enrich(IN_FILE=kor_file, **no_enrich_args)

    def test_ger(self):
        enrich(IN_FILE=ger_file, **no_enrich_args)

