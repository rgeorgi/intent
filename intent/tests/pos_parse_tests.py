from unittest import TestCase
from intent.corpora.POSCorpus import process_wsj_file
from intent.utils.dicts import CountDict

__author__ = 'rgeorgi'

class parse_wsj_tests(TestCase):

    def parse_test(self):
        path = '/Users/rgeorgi/Documents/treebanks/LDC95T07/RAW/combined/wsj/00/wsj_0001.mrg'

        tc = CountDict()

        def count_tokens(tokens):
            for token in tokens:
                tc.add(token.label)

        process_wsj_file(path, count_tokens)

        # There should be 31 total tokens in this file.
        self.assertEqual(31, tc.total())

        self.assertEqual(tc['.'], 2)


