import os
from unittest import TestCase
from intent.igt.igtutils import rgp
from intent.igt.rgxigt import RGCorpus, odin_ancestor, intervening_characters, morph_align
from intent.utils.env import proj_root, testfile_dir

__author__ = 'rgeorgi'


class MorphAlignTests(TestCase):

    def setUp(self):
        self.xc = RGCorpus.load(os.path.join(testfile_dir, 'xigt/morph_align_567.xml'))

    def test_intervening_characters(self):
        inst = self.xc[0]
        glosses = inst.glosses
        morphs  = inst.morphemes

        # Check for the intervening characters between
        # the first two morphs from the language line
        ichars = intervening_characters(morphs[0],morphs[1])

        # The intervening character should be a hyphen.
        self.assertEqual('-', ichars)

        # Now, check for the first two of the gloss line.
        gchars = intervening_characters(glosses[0], glosses[1])

        self.assertEqual('.', gchars)

        # And make sure that what is between the second and third
        # language morphemes is just whitespace.

        wchars = intervening_characters(morphs[1], morphs[2])

        self.assertEqual(' ', wchars)

        nochars = intervening_characters(morphs[1], morphs[1])

        self.assertEqual('', nochars)

    def morph_align_test(self):
        inst = self.xc[0]

        glosses = inst.glosses
        morphs = inst.morphemes

        morph_align(glosses, morphs)

        self.assertEqual(glosses[0].alignment, morphs[0].id)
        self.assertEqual(glosses[1].alignment, morphs[0].id)
        self.assertEqual(glosses[2].alignment, morphs[0].id)
        self.assertEqual(glosses[3].alignment, morphs[1].id)
        self.assertEqual(glosses[4].alignment, morphs[1].id)
        self.assertEqual(glosses[7].alignment, morphs[2].id)
        self.assertEqual(glosses[8].alignment, morphs[3].id)

    def more_morph_align_test(self):
        inst = self.xc[1]

        # Align the gloss/lang words (Needed for aligning morphs)
        inst.add_gloss_lang_alignments()

        glosses = inst.glosses
        morphs = inst.morphemes

        # Do the alignment
        morph_align(glosses, morphs)

        # Assert that the glosses are aligned...
        self.assertIsNotNone(glosses[0].alignment)

        self.assertEquals(glosses[11].alignment, morphs[6].id)
        self.assertEquals(glosses[12].alignment, morphs[6].id)
        self.assertEquals(glosses[13].alignment, morphs[7].id)
        self.assertEquals(glosses[14].alignment, morphs[7].id)
