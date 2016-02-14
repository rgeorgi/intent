import os
from unittest import TestCase

from intent.igt.create_tiers import morphemes, glosses, gloss, lang
from intent.igt.igt_functions import add_gloss_lang_alignments, intervening_characters, morph_align
from intent.igt.igtutils import rgp
from intent.igt.parsing import xc_load
from intent.utils.env import proj_root, testfile_dir, xigt_testfile

__author__ = 'rgeorgi'


class MorphAlignTests(TestCase):

    def setUp(self):
        self.xc = xc_load(os.path.join(testfile_dir, 'xigt/morph_align_567.xml'))

    def test_intervening_characters(self):
        inst = self.xc[0]
        gloss_tokens = glosses(inst)
        morph_tokens  = morphemes(inst)

        # Check for the intervening characters between
        # the first two morphs from the language line
        ichars = intervening_characters(morph_tokens[0],morph_tokens[1])

        # The intervening character should be a hyphen.
        self.assertEqual('-', ichars)

        # Now, check for the first two of the gloss line.
        gchars = intervening_characters(gloss_tokens[0], gloss_tokens[1])

        self.assertEqual('.', gchars)

        # And make sure that what is between the second and third
        # language morphemes is just whitespace.

        wchars = intervening_characters(morph_tokens[1], morph_tokens[2])

        self.assertEqual(' ', wchars)

        nochars = intervening_characters(morph_tokens[1], morph_tokens[1])

        self.assertEqual('', nochars)

    def morph_align_test(self):
        inst = self.xc[0]

        gloss_tokens = glosses(inst)
        morph_tokens = morphemes(inst)

        morph_align(gloss_tokens, morph_tokens)

        self.assertEqual(gloss_tokens[0].alignment, morph_tokens[0].id)
        self.assertEqual(gloss_tokens[1].alignment, morph_tokens[0].id)
        self.assertEqual(gloss_tokens[2].alignment, morph_tokens[0].id)
        self.assertEqual(gloss_tokens[3].alignment, morph_tokens[1].id)
        self.assertEqual(gloss_tokens[4].alignment, morph_tokens[1].id)
        self.assertEqual(gloss_tokens[7].alignment, morph_tokens[2].id)
        self.assertEqual(gloss_tokens[8].alignment, morph_tokens[3].id)

    def more_morph_align_test(self):
        inst = self.xc[1]

        # Align the gloss/lang words (Needed for aligning morphs)
        add_gloss_lang_alignments(inst)

        gloss_tokens = glosses(inst)
        morph_tokens = morphemes(inst)

        # Do the alignment
        morph_align(gloss_tokens, morph_tokens)

        # Assert that the glosses are aligned...
        self.assertIsNotNone(gloss_tokens[0].alignment)

        self.assertEquals(gloss_tokens[11].alignment, morph_tokens[6].id)
        self.assertEquals(gloss_tokens[12].alignment, morph_tokens[6].id)
        self.assertEquals(gloss_tokens[13].alignment, morph_tokens[7].id)
        self.assertEquals(gloss_tokens[14].alignment, morph_tokens[7].id)

class NewMorphAlignTests(TestCase):
    def setUp(self):
        self.xc = xc_load(xigt_testfile('word_align.xml'))

    def test_line_lengths(self):
        inst = self.xc[1]
        self.assertEqual(5, len(gloss(inst)))
        self.assertEqual(6, len(lang(inst)))

    def test_word_alignment(self):
        inst = self.xc[1]
        add_gloss_lang_alignments(inst)
        rgp(inst)

