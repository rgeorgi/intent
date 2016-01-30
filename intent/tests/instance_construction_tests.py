from unittest import TestCase

from intent.igt.igt_functions import add_raw_tier, add_clean_tier, add_normal_tier
from intent.igt.references import raw_tier, cleaned_tier, normalized_tier
from intent.igt.rgxigt import Igt


class ConstructIGTTests(TestCase):

    def setUp(self):
        self.lines = [{'text':'This is a test','tag':'L'},
                      {'text':'blah blah blah blah','tag':'G'}]

    def test_add_raw_lines(self):
        inst = Igt(id='i1')
        add_raw_tier(inst, self.lines)
        self.assertEqual(len(raw_tier(inst)), 2)

    def test_add_clean_lines(self):
        inst = Igt(id='i1')
        add_clean_tier(inst, self.lines)
        self.assertEqual(len(cleaned_tier(inst)), 2)

    def test_add_norm_lines(self):
        inst = Igt(id='i1')
        add_normal_tier(inst, self.lines)
        self.assertEqual(len(normalized_tier(inst)), 2)