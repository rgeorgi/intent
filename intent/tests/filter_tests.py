from unittest import TestCase

from intent.commands.filter import filter_xc
from intent.igt.parsing import xc_load
from intent.utils.env import xigt_testfile


class FilterTests(TestCase):

    def test_filter_gloss_not_present(self):
        xp = xigt_testfile('missing_line_tests.xml')
        xc = xc_load(xp)

        test_xc, ex, fail, succ = filter_xc(xc, require_gloss=True)
        self.assertEqual(len(test_xc), 2)

        test_xc, ex, fail, succ = filter_xc(xc, require_gloss=False)
        self.assertEqual(len(test_xc), 3)

        test_xc, ex, fail, succ = filter_xc(xc, require_gloss=True, require_trans=True)
        self.assertEqual(len(test_xc), 1)

        test_xc, ex, fail, succ = filter_xc(xc, require_aln=True)
        self.assertEqual(len(test_xc), 0)

        test_xc, ex, fail, succ = filter_xc(xc, require_trans=True)
        self.assertEqual(len(test_xc), 2)

