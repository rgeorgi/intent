import unittest

import intent
from intent.igt.rgxigt import RGWordTier
from intent.trees import IdTree, project_ps, TreeMergeError


__author__ = 'rgeorgi'

class ProjectTest(unittest.TestCase):

    def setUp(self):
        self.t = IdTree.fromstring('''
        (S
            (NP
                (DT The)
                (NN teacher)
            )
            (VP
                (VBD gave)
                (NP
                    (DT a)
                    (NN book)
                )
                (PP
                    (IN to)
                    (NP
                        (DT the)
                        (NN boy)
                    )
                )
                (NP
                    (NN yesterday)
                )
            )
        )''')
        self.proj = IdTree.fromstring(
            '''(S
                (VBD rhoddodd)
                (NP
                    (DT yr)
                    (NN athro)
                )
                (NP
                    (NN lyfr)
                )
                (PP
                    (IN+DT i'r)
                    (NN bachgen)
                )
                (NP
                    (NN ddoe)
                )
            )''')
        self.aln = intent.alignment.Alignment.Alignment([(1,2), (2,3), (3,1), (5,4), (6, 5), (7, 5), (8, 6), (9, 7)])

    def test_projection(self):
        proj = project_ps(self.t, RGWordTier.from_string("rhoddodd yr athro lyfr i'r bachgen ddoe"), self.aln)

        # Reassign the ids after everything has moved around.
        proj.assign_ids()

        self.assertEqual(self.proj, proj)

class PromoteTest(unittest.TestCase):

    def setUp(self):
        self.t = IdTree.fromstring('(S (NP (DT the) (NN boy)) (VP (VBD ran) (IN away)))')

    def test_equality(self):
        t2 = self.t.copy()
        t3 = self.t.copy()
        self.assertEqual(self.t, t2)

        t2.find_index(1).delete()
        self.assertNotEqual(self.t, t2)

        # Change the id
        t3n = t3.find_index(1)
        t3id = t3n.id

        t3n.id = 'asdf'

        self.assertNotEqual(self.t, t3)

        # Change it back.
        t3n.id = t3id
        self.assertEqual(self.t, t3)


    def test_promote(self):
        t2 = self.t.copy()
        t3 = self.t.copy()
        vp = self.t[1]
        vp.promote()

        self.assertNotEqual(self.t, t2)
        self.assertEqual(t2, t3)

class SpanTest(unittest.TestCase):

    def setUp(self):
        self.t = IdTree.fromstring('''(ROOT
                                          (SBARQ
                                            (WHNP (WP Who))
                                            (SQ (VBP do)
                                                (NP (PRP you))
                                            (VP (VB believe)
                                                (VP (VBN called))))))'''
        )

    def test_span(self):
        self.assertEqual(self.t.span(), (1,5))

class MergeTests(unittest.TestCase):
    def setUp(self):
        self.t = IdTree.fromstring('''(ROOT
                                          (SBARQ
                                            (WHNP (WP Who))
                                            (SQ (VBP do)
                                                (NP (PRP you))
                                            (VP (VB believe)
                                                (VP (VBN called))))))''')

    def test_merge_interior_nodes(self):
        t = self.t.copy()

        t[0].merge(0, 1, unify_children=False)

        self.assertNotEqual(t, self.t)

        t2 = IdTree.fromstring('''(ROOT (SBARQ (WHNP+SQ
                                                (WP Who)
                                                (VBP do)
                                                (NP (PRP you))
                                                (VP (VB believe)
                                                    (VP (VBN called))
                                                ))
                                        ))''')
        self.assertTrue(t2.similar(t))
        self.assertEqual(t2[0,0].label(), 'WHNP+SQ')

        t[(0,0)].merge(0,1, unify_children=False)
        self.assertEquals(t[(0,0,0)].span(), (1,2))

    def test_merge_preterminal_nodes_no_unify(self):
        t = IdTree.fromstring('''(NP (DT The) (NN Boy) (VB Ran))''')

        self.assertEqual(t.span(), (1,3))
        self.assertEqual(t[0].span(), (1,1))
        self.assertEqual(t[1].span(), (2,2))
        t.merge(0,1, unify_children=False)
        self.assertEqual(t[0].label(), 'DT+NN')
        self.assertEqual(t[0].span(), (1,2))
        self.assertEqual(t.span(), (1,3))

    def test_merge_preterminal_nodes_unify(self):
        t = IdTree.fromstring('''(NP (DT The) (NN The) (VB Ran))''')

        l = t.leaves()
        l[0].index = 1
        l[1].index = 1
        l[2].index = 2

        self.assertEqual(t.span(), (1,2))
        self.assertEqual(t[0].span(), (1,1))
        self.assertEqual(t[1].span(), (1,1))

        t.merge(0,1, unify_children=True)
        self.assertEqual(t[0].label(), 'DT+NN')
        self.assertEqual(t[0].span(), (1,1))
        self.assertEqual(t.span(), (1,2))


    def test_merge_preterminal_and_nonterminal(self):
        t = self.t.copy()

        sq = t[0,1,2]
        self.assertEqual(sq.span(), (4,5))

        self.assertRaises(TreeMergeError, sq.merge, 0,1)


