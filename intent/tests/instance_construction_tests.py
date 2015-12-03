from unittest import TestCase

from intent.igt.rgxigt import RGIgt


class ConstructIGTTests(TestCase):

    def setUp(self):
        self.lines = [{'text':'This is a test','tag':'L'},
                      {'text':'blah blah blah blah','tag':'G'}]

    def test_add_raw_lines(self):
        inst = RGIgt(id='i1')
        inst.add_raw_tier(self.lines)
        self.assertEqual(len(inst.raw_tier()), 2)

    def test_add_clean_lines(self):
        inst = RGIgt(id='i1')
        inst.add_clean_tier(self.lines)
        self.assertEqual(len(inst.clean_tier()), 2)

    def test_add_norm_lines(self):
        inst = RGIgt(id='i1')
        inst.add_clean_tier(self.lines)
        self.assertEqual(len(inst.clean_tier()), 2)