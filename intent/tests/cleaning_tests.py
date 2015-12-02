from unittest import TestCase

from intent.igt.igtutils import strip_leading_whitespace, clean_lang_string, clean_trans_string


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
        l6 = "      `I read her article.'                     `I read one of her articles."

        newlines = [l4,l5,l6]

        self.assertEqual(newlines, line_result)

    def clean_lang_test(self):
        result = clean_lang_string(self.l1)
        self.assertEqual(result, '          Procetox        statija-ta=i.          (ii) *Procetox statija=i.')

    def clean_trans_test(self):
        print(clean_trans_string(self.l3))
