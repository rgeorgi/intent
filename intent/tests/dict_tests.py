from unittest import TestCase
from intent.utils.dicts import POSEvalDict

__author__ = 'rgeorgi'

class POSEvalTests(TestCase):

    def first_test(self):
        d = POSEvalDict()

        d.add('NOUN', 'NOUN')
        d.add('NOUN', 'VERB')

        self.assertEqual(d.recall(), 50.)
        self.assertEqual(d.accuracy(), 50.)
        self.assertEqual(d.precision(), 50.)

    def second_test(self):
        d = POSEvalDict()
        d.add('NOUN', 'NOUN')
        d.add('NOUN', 'VERB')
        d.add('NOUN', 'VERB')
        d.add('VERB', 'NOUN')
        d.add('VERB', 'VERB')

        self.assertAlmostEqual(d.recall(), 40)
        self.assertAlmostEqual(d.precision(), 40)
        self.assertAlmostEqual(d.accuracy(), 40)

        self.assertAlmostEqual(d.tag_recall('NOUN'), 33.3, places=1)
        self.assertAlmostEqual(d.tag_precision('NOUN'), 50.0)
        self.assertAlmostEqual(d.tag_recall('VERB'), 50, places=1)
        self.assertAlmostEqual(d.tag_precision('VERB'), 33.3, places=1)




