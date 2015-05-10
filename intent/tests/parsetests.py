import os
from unittest import TestCase
from intent.subcommands import enrich
from intent.utils.arg_consts import POS_VAR, POS_LANG_PROJ, ALN_HEUR, ALN_VAR, POS_LANG_CLASS
from intent.utils.env import proj_root

__author__ = 'rgeorgi'

example_dir = os.path.join(proj_root, './examples')

ctn_file = os.path.join(example_dir, 'ctn2-xigt.xml')
ger_file = os.path.join(example_dir, 'single_ger.xml')
kor_file = os.path.join(example_dir, 'kor-ex.xml')

test_dir = os.path.join(example_dir, "tests")

# Different testing files
odin_file = os.path.join(test_dir, 'odin-tests.xml')
emily_file = os.path.join(test_dir, '567-testsuite.xml')
ctn_file  = os.path.join(test_dir, 'ctn-train-tests.xml')

# Different arguments
no_enrich_args = {'OUT_FILE':'/dev/null'}
proj_pos_args  = {'OUT_FILE':'/dev/null', POS_VAR:[POS_LANG_PROJ], ALN_VAR:[ALN_HEUR]}
class_pos_args = {'OUT_FILE':'/dev/null', POS_VAR:[POS_LANG_CLASS]}

class ParseTests(TestCase):

    def test_ctn(self):
        enrich(IN_FILE=ctn_file, **no_enrich_args)

    def test_kor(self):
        enrich(IN_FILE=kor_file, **no_enrich_args)

    def test_ger(self):
        enrich(IN_FILE=ger_file, **no_enrich_args)


class ODINTests(TestCase):

    def test_parse(self):
        enrich(IN_FILE=odin_file, **no_enrich_args)

    def test_proj(self):
        enrich(IN_FILE=odin_file, **proj_pos_args)

    def test_class(self):
        enrich(IN_FILE=odin_file, **class_pos_args)

class emily_567_tests(TestCase):
    def test_parse(self):
        enrich(IN_FILE=emily_file, **no_enrich_args)

    def test_proj(self):
        enrich(IN_FILE=emily_file, **proj_pos_args)

    def test_class(self):
        enrich(IN_FILE=emily_file, **class_pos_args)

class ctn_train_tests(TestCase):
    def test_parse(self):
        enrich(IN_FILE=ctn_file, **no_enrich_args)

    def test_proj(self):
        enrich(IN_FILE=ctn_file, **proj_pos_args)

    def test_class(self):
        enrich(IN_FILE=ctn_file, **class_pos_args)