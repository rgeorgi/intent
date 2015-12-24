import os
from unittest import TestCase
from xigt.codecs import xigtxml
from intent.utils.env import testfile_dir


class TestTierSort(TestCase):

    def setUp(self):
        my_path = os.path.join(testfile_dir, 'xigt/kor-ex.xml')
        self.my_igt = xigtxml.load(my_path)

    def test_tier_sort(self):
        igt = self.my_igt[0]
        igt.sort_tiers()
        tier_ids = [t.id for t in igt.tiers]
        goal_ids = ['o', 'c', 'n', 'p', 'w', 'm', 'g', 'w-pos', 't', 'tw', 'tw-pos', 'ps', 'a', 'dt', 'dtb']
        self.assertEqual(tier_ids, goal_ids)
