from unittest import TestCase

from intent.alignment.Alignment import Alignment, heuristic_iteration, exact_match, stem_match, gram_match, \
    heuristic_chain


class symmetricization_tests(TestCase):

    def setUp(self):
        self.a1 = Alignment([(1,1),(2,1),(3,2)])
        self.a2 = Alignment([(1,1),(3,2),(4,4)])

    def intersect_test(self):
        a_tgt = Alignment([(3,2),(1,1)])
        self.assertEqual(a_tgt, self.a1.intersection(self.a2))

    def test_union(self):
        a_tgt = Alignment([(1,1),(2,1),(3,2),(4,4)])
        self.assertEqual(a_tgt, self.a1.union(self.a2))

    def test_grow_diag(self):

        a = Alignment([(3,2),(1,1),(2,1)])
        self.assertEqual(a, self.a1.grow_diag(self.a2))

    def test_grow_diag_final(self):
        #TODO: Write testcase for grow_diag_final
        raise Exception("NO TESTCASE DEFINED!")

class heur_align_tests(TestCase):

    def setUp(self):
        self.gloss = "1SG feels the Cat NOM kicks the ACC dog".split()
        self.trans = "I   feel that the cat kicked the dog".split()

        self.exact = Alignment([(3, 4), (7, 7), (9, 8)])
        self.stem  = Alignment([(2, 2), (3, 4), (4, 5), (6, 6), (7, 7), (9, 8)])
        self.gram  = Alignment([(1, 1)])
        self.all   = Alignment([(1, 1), (2, 2), (3, 4), (4, 5), (6, 6), (7, 7), (9, 8)])

    def _harness(self, f):
        return heuristic_iteration(self.gloss, self.trans, Alignment(), f)

    def test_exact(self):
        self.assertEqual(self.exact, self._harness(exact_match))

    def test_stem(self):
        self.assertEqual(self.stem, self._harness(stem_match))

    def test_gram(self):
        self.assertEqual(self.gram, self._harness(gram_match))

    def test_heur_chain(self):
        print(sorted(heuristic_chain(self.gloss, self.trans, [exact_match, stem_match, gram_match])))
