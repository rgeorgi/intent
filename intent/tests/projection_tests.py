import os
from unittest import TestCase

from intent.commands.enrich import enrich
from intent.commands.project import do_projection
from intent.consts import *
from xigt.codecs import xigtxml

from intent.utils.env import testfile_dir

dep_path = os.path.join(testfile_dir, 'xigt/dependency_tests.xml')
ps_path  = os.path.join(testfile_dir, 'xigt/phrase_structure_tests.xml')

class test_dep_proj(TestCase):

    def test_inst_1(self):
        kwargs = {ARG_INFILE:dep_path,
                  ARG_OUTFILE:'/dev/null',
                  ALN_VAR:[ARG_ALN_HEUR],
                  PARSE_VAR:[ARG_PARSE_LANG, ARG_PARSE_TRANS]}
        self.assertIsNone(enrich(**kwargs))


class test_ps_proj(TestCase):
    def test_inst_1(self):
        kwargs={ARG_INFILE:ps_path,
                ARG_OUTFILE:'/dev/null',
                'aln_method':ARG_ALN_HEUR}
        do_projection(**kwargs)
