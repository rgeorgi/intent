from unittest import TestCase

from intent.igt.igtutils import clean_gloss_string, hyphenate_infinitive, merge_lines


class TestGlossLines(TestCase):
    def test_gloss(self):
        g1 = 'Agnès     1SG . REC   3SG . M . THM   present. FUT .3 SG'

        g1_clean = clean_gloss_string(g1)
        g1_target = 'Agnès     1SG.REC   3SG.M.THM   present.FUT.3SG'

        self.assertEquals(g1_clean, g1_target)


class TestHyphenate(TestCase):
    def runTest(self):
        h1 = 'the guests wanted to visit the other pavilion'
        h1f = 'the guests wanted to-visit the other pavilion'

        self.assertEqual(hyphenate_infinitive(h1), h1f)


class TestMergeLines(TestCase):
    def runTest(self):
        l1 = 'This        an example          merged lines'
        l2 = '      is         sdfa     of                '

        merged = merge_lines([l1, l2])
        tgt = 'This  is    an example    of    merged lines'
        self.assertEqual(merged, tgt)

