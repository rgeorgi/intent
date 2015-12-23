import os
from unittest import TestCase

from xigt.codecs import xigtxml

from intent.igt.rgxigt import RGCorpus, tier_sorter, sort_igt
from intent.utils.env import testfile_dir


class TestTierSort(TestCase):

    def setUp(self):
        my_path = os.path.join(testfile_dir, 'xigt/kor-ex.xml')
        self.my_igt = xigtxml.load(my_path)

    def test_tier_sort(self):
        igt = sort_igt(self.my_igt[0])
        # igt = self.my_igt[0]
        # igt.sort(key=tier_sorter)
        tier_ids = [t.id for t in igt.tiers]
        self.assertEqual(tier_ids, ['o', 'c', 'n', 'p', 'w', 'm', 'w-pos', 'g', 't', 'tw', 'tw-pos', 'ps', 'dt', 'dtb', 'a'])
