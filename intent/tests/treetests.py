import unittest

import intent
from intent.alignment.Alignment import Alignment
from intent.igt.rgxigt import RGWordTier
from intent.trees import IdTree, project_ps, TreeMergeError, DepTree, Terminal, TreeError


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

    def test_duplicates(self):
        """
        Test the case where an English word aligns to multiple language words.

        """
        src_t = IdTree.fromstring('(ROOT (SBARQ (WHNP (WP Who)) (SQ (VP (VBZ else?)))))')
        tgt_w = RGWordTier.from_string('sa-lo sa-lo')
        tgt_t = IdTree.fromstring('(ROOT (SBARQ (WHNP (WP sa-lo) (WP sa-lo))))')
        aln = Alignment([(1,1),(1,2)])

        result = project_ps(src_t, tgt_w, aln)

        self.assertTrue(tgt_t.similar(result))

    def ordering_test(self):
        """
        This particular tree structure results in changing a child of a tree while iterating through
        the children and required a fix such that if such a change is detected, we start iterating
        over the children again, so we're not holding onto a stale pointer.

        """
        src_t = IdTree.fromstring('''(ROOT (FRAG
                                            (ADVP (RB Probably))
                                            (SBAR (S
                                                    (NP (PRP you))
                                                    (VP (VBP find)
                                                        (ADJP (JJ something))
                                                    )
                                                  )
                                            )
                                           ))''')

        tgt_t = IdTree.fromstring('''(ROOT (FRAG
                                                (VBP chitt-u-m)
                                                (ADVP (RB hola))
                                                (UNK ni)
                                                (UNK hou)
                                                (VBP chitt-u-m)
                                            ))''')
        tgt_w = RGWordTier.from_string('''chitt-u-m hola ni hou chitt-u-m''')
        aln = Alignment([(1,2),(3,1),(3,5)])

        proj = project_ps(src_t, tgt_w, aln)

        self.assertTrue(tgt_t.similar(proj))



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


class DepTreeTests(unittest.TestCase):

    def setUp(self):
        dt_string = '''nsubj(ran-2, John-1)
                       root(ROOT-0, ran-2)
                       det(woods-5, the-4)
                       prep_into(ran-2, woods-5)'''
        self.dt = DepTree.fromstring(dt_string)

    def test_find(self):
        j = self.dt.find_index(1)
        self.assertEqual(j, DepTree('John', [], id=j.id, word_index=1, type='nsubj'))

    def test_copy(self):
        t2 = self.dt.copy()
        self.assertEqual(self.dt, t2)

    def test_equality(self):
        t2 = self.dt.copy()
        t2._word_index = -1
        self.assertNotEqual(t2, self.dt)
        t2._word_index = 0
        self.assertEqual(t2, self.dt)
        t2._label = 'notroot'
        self.assertNotEqual(t2, self.dt)

    def test_span(self):
        self.assertRaises(TreeError, self.dt.span)

class SwapTests(unittest.TestCase):
    def setUp(self):
        self.t = IdTree.fromstring('''(S (NP (DT The) (NN Boy)) (VP (VB Ran) ))''')
        self.t2 = IdTree.fromstring('''(NP (DT The) (ADJ quick) (NN Fox))''')

    def test_swap_nonterminals(self):
        t = self.t.copy()
        t.swap(0, 1)

        # Now, set up the leaves with the correct indices...
        t2 = IdTree.fromstring('''(S (VP (VB Ran)) (NP (DT The) (NN Boy)))''')
        l = t2.leaves()

        l[0].index = 3
        l[1].index = 1
        l[2].index = 2

        self.assertTrue(t.similar(t2))

    def test_swap_preterminals(self):
        t2 = self.t2.copy()
        t2.swap(0,2)

        t3 = IdTree.fromstring('''(NP (NN Fox) (DT quick) (ADJ The))''')
        l = t3.leaves()
        l[0].index = 3
        l[2].index = 1

        self.assertTrue(t2.similar(t3))

class DeleteTests(unittest.TestCase):
    def setUp(self):
        self.t = IdTree.fromstring('''(ROOT (NP (DT The) (NP (NN Boy))))''')

    def propagate_test(self):
        tgt = IdTree.fromstring('''(ROOT (NP (DT The)))''')

        self.assertFalse(self.t.similar(tgt))

        # Delete the "NN" in boy.
        self.t[0,1,0].delete()

        self.assertTrue(self.t.similar(tgt))

    def replace_test(self):
        tgt = IdTree.fromstring('''(ROOT (NP (DT The) (NN Dog)))''')

        self.assertFalse(self.t.similar(tgt))

        # Replace the "NP" in (NP (NN Boy)) with (NN Dog)
        self.t[0,1].replace(IdTree('NN',[Terminal('Dog', index=2)]))

        self.assertTrue(self.t.similar(tgt))