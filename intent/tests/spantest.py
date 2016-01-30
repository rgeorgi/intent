import os
from unittest import TestCase

from intent.igt.igt_functions import odin_span, x_contains_y, x_span_contains_y
from intent.igt.parsing import xc_load
from intent.igt.references import xigt_find
from intent.utils.env import testfile_dir
from xigt.model import Item

__author__ = 'rgeorgi'

class span_test(TestCase):
    def setUp(self):
        self.xc1 = xc_load(os.path.join(testfile_dir, 'xigt/kor-ex.xml'))
        self.inst = self.xc1[0]
        self.g1_2 = xigt_find(self.inst, id='g1.2')
        self.m2_1 = xigt_find(self.inst, id="m2.1")
        self.p1 = xigt_find(self.inst, id='p1')
        self.w1 = xigt_find(self.inst, id="w1")
        self.m_tier = xigt_find(self.inst, id="m")
        self.new_m = Item(id="m5", tier=self.m_tier, segmentation="w1[0:2]+w4[2:3]")

    def test_spans(self):
        self.assertEqual(odin_span(self.p1), [(0,35)])
        self.assertEqual(odin_span(self.g1_2), [(2,5)])
        self.assertEqual(odin_span(self.m2_1), [(7,9)])
        self.assertEqual(odin_span(self.w1), [(0,6)])
        self.assertEqual(odin_span(self.new_m), [(0,2),(25,26)])

    def test_contains(self):
        self.assertTrue(x_contains_y(self.inst, self.p1, self.m2_1))
        self.assertFalse(x_contains_y(self.inst, self.m2_1, self.p1))

#===============================================================================
# Span Tests
#===============================================================================
class ContainsTests(TestCase):

    def test_contains_simple(self):
        spanlist_a = [(2,5)]
        spanlist_b = [(1,5)]
        spanlist_c = [(3,5)]
        spanlist_d = [(3,4)]
        spanlist_e = [(2,7)]

        self.assertTrue(x_span_contains_y(spanlist_b, spanlist_b))
        self.assertTrue(x_span_contains_y(spanlist_b, spanlist_a))
        self.assertTrue(x_span_contains_y(spanlist_a, spanlist_d))
        self.assertFalse(x_span_contains_y(spanlist_c, spanlist_b))
        self.assertFalse(x_span_contains_y(spanlist_e, spanlist_b))

    def test_contains_complex(self):
        spanlist_a = [(1, 4), (5, 7)]
        spanlist_b = [(1, 7)]

        spanlist_c = [(1, 4), (8, 10)]
        spanlist_d = [(0, 5), (7, 10), (11, 14)]

        self.assertTrue(x_span_contains_y(spanlist_b, spanlist_a))
        self.assertTrue(x_span_contains_y(spanlist_d, spanlist_c))
        self.assertFalse(x_span_contains_y(spanlist_d, spanlist_a))

