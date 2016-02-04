from unittest import TestCase

from intent.alignment.Alignment import Alignment
from intent.igt.igtutils import strip_leading_whitespace, clean_lang_string, clean_trans_string, strict_columnar_alignment, \
    is_strict_columnar_alignment
from intent.utils.token import tokenize_string, sentence_tokenizer


class CleanTests(TestCase):

    def setUp(self):
        self.l1 = '      (i) Procetox        statija-ta=i.          (ii) *Procetox statija=i.'
        self.l2 = '            read.1sg      article-DEF=3fsg            read.1sg     article=3fsg'
        self.l3 = "            `I read her article.'                     `I read one of her articles.'"

        self.lines = [self.l1, self.l2, self.l3]

    def clean_lines_test(self):

        line_result = strip_leading_whitespace(self.lines)

        l4 = '(i) Procetox        statija-ta=i.          (ii) *Procetox statija=i.'
        l5 = '      read.1sg      article-DEF=3fsg            read.1sg     article=3fsg'
        l6 = "      `I read her article.'                     `I read one of her articles.'"

        newlines = [l4,l5,l6]

        self.assertEqual(newlines, line_result)

    def clean_lang_test(self):
        result = clean_lang_string(self.l1)
        self.assertEqual(result, '          Procetox        statija-ta=i.               *Procetox statija=i ')

    def clean_trans_test(self):
        result = "             I read her article.'                     `I read one of her articles  "
        self.assertEqual(clean_trans_string(self.l3), result)


    def clean_new_trans_test(self):
        orig = '"I don\'t understand any of it; I don\'t understand it at all"'
        expected = " I don\'t understand any of it; I don\'t understand it at all "
        result = clean_trans_string(orig)

        self.assertEqual(result, expected)

        tokenized          = tokenize_string(result, tokenizer=sentence_tokenizer).text()
        tokenized_expected = "I don't understand any of it ; I don't understand it at all"
        self.assertEqual(tokenized, tokenized_expected)

class AlignTests(TestCase):

    def setUp(self):
        self.l1 = 'Procetox ts     statija-ta=i'
        self.l2 = 'read.1sg.FEM    article DEF'


    def test_columnar_alignment(self):
        result = strict_columnar_alignment(self.l1, self.l2)

        a = Alignment([(1,1),(2,1),(3,2),(3,3)])
        self.assertEqual(a, result)

    def test_is_strict_columnar(self):
        self.assertTrue(is_strict_columnar_alignment(self.l1, self.l2))

