from unittest import TestCase

from intent.igt.rgxigt import RGIgt,  RGTier, gen_item_id, gen_tier_id

__author__ = 'rgeorgi'

class IdTests(TestCase):
    """
    Tests for asserting that the ID generation
    functions as expected.
    """

    def standard_id_test(self):
        self.assertEqual('i1', gen_item_id('i', 0))

class TierIdTests(TestCase):
    def setUp(self):
        self.i = RGIgt(id='i1')
        self.i.append(RGTier(id='tw'))
        self.i.append(RGTier(id='w'))

    def same_type_different_tiers_test(self):
        pos1_id = gen_tier_id(self.i, 'pos', tier_type='pos', alignment='tw')
        self.assertEqual(pos1_id, 'tw-pos')

        self.i.append(RGTier(id=pos1_id, type='pos', alignment='tw'))
        pos2_id = gen_tier_id(self.i, 'pos', tier_type='pos', alignment='tw')
        self.assertEqual(pos2_id, 'tw-pos_b')

    def unique_tier_test(self):
        tw_id = gen_tier_id(self.i, 'w', tier_type='words', alignment='t', no_hyphenate=True)
        print(tw_id)