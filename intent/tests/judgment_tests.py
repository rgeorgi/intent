from unittest import TestCase

from xigt.codecs import xigtxml

from intent.consts import ODIN_LANG_TAG, ODIN_JUDGMENT_ATTRIBUTE, ODIN_TRANS_TAG
from intent.igt.create_tiers import retrieve_normal_lines, generate_lang_phrase_tier, generate_trans_phrase_tier
from intent.igt.igtutils import get_judgment, extract_judgment
from intent.tests.parsetests import ger_file


class JudgmentTests(TestCase):

    def ungrammatical_test(self):
        l1 = "             *'Read many   books, she has'"
        self.assertEqual(get_judgment(l1), '*')

    def test_extract_ungrammatical(self):
        l1 = "             '*Read many   books, she has'"
        result, j = extract_judgment(l1)
        self.assertEqual(result, "             ' Read many   books, she has'")
        self.assertEqual(j, '*')

    def test_extract_questionable(self):
        l1 = " ?This statement is questionable"
        r1 = "  This statement is questionable"
        l2 = "  This statement is a question?"
        r2 = "  This statement is a question?"

        result, j = extract_judgment(l1)
        self.assertEqual(result, r1)
        self.assertEqual(j, '?')

        result, j = extract_judgment(l2)
        self.assertEqual(result, r2)
        self.assertEqual(j, None)

    def test_extract_none(self):
        l1 = "  This statement is fine"
        r1 = "  This statement is fine"

        result, j = extract_judgment(l1)
        self.assertEqual(result, r1)
        self.assertEqual(j, None)

    def questionable_test(self):
        l1 = "        b. ?Koja ot tezi knigi se ¤cudi      ¤s   koj    znae     koj prodava?"
        l2 = "        b.  Koja ot tezi knigi se ¤cudi      ¤s   koj    znae     koj prodava?"
        l3 = "*       b. ?Koja ot tezi knigi se ¤cudi      ¤s   koj    znae     koj prodava?"
        l4 = "?*      b.  Koja ot tezi knigi se ¤cudi      ¤s   koj    znae     koj prodava?"
        self.assertEqual(get_judgment(l1), None)
        self.assertEqual(get_judgment(l2), None)
        self.assertEqual(get_judgment(l3), '*')
        self.assertEqual(get_judgment(l4), '?*')


# -------------------------------------------
# Test the propagation of the judgment attribute
# from an odin line to the phrase item it
# creates.
# -------------------------------------------
class JudgmentPropogationTests(TestCase):

    def setUp(self):
        xc = xigtxml.load(ger_file)
        self.inst = xc[0]

    def test_lang_line_propogation(self):

        # Get the language line...
        lang_line = retrieve_normal_lines(self.inst, ODIN_LANG_TAG)[0]
        lang_line.attributes[ODIN_JUDGMENT_ATTRIBUTE] = '*'

        phrase_item = generate_lang_phrase_tier(self.inst)[0]

        self.assertEqual(phrase_item.attributes.get(ODIN_JUDGMENT_ATTRIBUTE), '*')

    def test_trans_line_propogation(self):
        trans_line = retrieve_normal_lines(self.inst, ODIN_TRANS_TAG)[0]
        trans_line.attributes[ODIN_JUDGMENT_ATTRIBUTE] = '*'

        phrase_item = generate_trans_phrase_tier(self.inst)[0]
        self.assertEqual(phrase_item.attributes.get(ODIN_JUDGMENT_ATTRIBUTE), '*')
