import os
from unittest import TestCase
import logging
# logging.basicConfig(level=logging.DEBUG)

from intent.commands.enrich import enrich
from intent.commands.project import do_projection
from intent.consts import *
from intent.igt.parsing import xc_load
from xigt.codecs import xigtxml

from intent.utils.env import testfile_dir, xigt_testfile

dep_path = os.path.join(testfile_dir, 'xigt/dependency_tests.xml')
ps_path  = os.path.join(testfile_dir, 'xigt/phrase_structure_tests.xml')

class test_dep_proj(TestCase):

    def test_inst_1(self):
        kwargs = {ARG_INFILE:dep_path,
                  ARG_OUTFILE:'/dev/null',
                  ALN_VAR:[ARG_ALN_HEUR],
                  PARSE_VAR:[ARG_PARSE_PROJ, ARG_PARSE_TRANS]}
        self.assertIsNone(enrich(**kwargs))

    def test_inst_2(self):
        xp = xigt_testfile('xigt-projection-tests.xml')
        xc = xc_load(xp)
        do_projection(**{ARG_INFILE:xp, 'aln_method':ARG_ALN_GIZA, ARG_OUTFILE:'/dev/null'})



class test_ps_proj(TestCase):
    def test_inst_1(self):
        kwargs={ARG_INFILE:ps_path,
                ARG_OUTFILE:'/dev/null',
                'aln_method':ARG_ALN_HEUR}
        do_projection(**kwargs)
