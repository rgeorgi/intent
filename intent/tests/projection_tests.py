import os
from unittest import TestCase

from intent.subcommands import enrich
from intent.utils.arg_consts import ALN_VAR, PARSE_VAR
from xigt.codecs import xigtxml

from intent.utils.env import testfile_dir

dep_path = os.path.join(testfile_dir, 'xigt/dependency_tests.xml')

class test_dep_proj(TestCase):

    def test_inst_1(self):
        kwargs = {'IN_FILE':dep_path,
                  'OUT_FILE':'/Users/rgeorgi/test.xml',
                  ALN_VAR:['heur'],
                  PARSE_VAR:['proj','trans']}
        self.assertIsNone(enrich(**kwargs))

