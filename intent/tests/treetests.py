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

    def failed_insertion_test(self):
        t = IdTree.fromstring('''(ROOT
  (SBARQ
    (WHNP (WDT What) (NP (NN kind) (PP (IN of) (NP (NNP work,)))))
    (SQ (VP (VBZ then?)))))''')
        tgt_w = RGWordTier.from_string('kam-a na them lis-no-kha hou')
        aln = Alignment([(1, 3), (2, 5), (4, 1), (5, 5)])

        project_ps(t, tgt_w, aln)

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


    def test_merge_preterminal_and_nonterminal_wo_unify(self):
        t = self.t.copy()

        sq = t[0,1,2]
        self.assertEqual(sq.span(), (4,5))

        sq.merge(0,1, unify_children=False)

        self.assertEqual(sq.span(), (4,5))
        self.assertEqual(len(sq[0]), 2)

    def test_merge_preterminal_and_nonterminal_w_unify(self):
        t = self.t.copy()

        sq = t[0,1,2]
        self.assertEqual(sq.span(), (4,5))

        sq.merge(0,1, unify_children=True)

        self.assertEqual(sq.spanlength(), 0)
        self.assertEqual(len(sq[0]), 1)



    def internal_merge_test(self):
        t = IdTree.fromstring('''(ROOT
                                  (UCP
                                    (S
                                      (NP (PRP u-tus-u-kV-nɨŋ))
                                      (VP
                                        (RB u-tus-u-kV-nɨŋ)
                                        (ADJP
                                          (RB loĩs-ma)
                                          (JJ loĩs-ma)
                                          (S (VP (VP (VB loĩs-ma) (NP (PRP kat-a-ŋs-e)) (ADVP (RB loĩs-ma))))))))
                                    (SBAR
                                      (IN loĩs-ma)
                                      (S
                                        (NP (PRP u-tus-u-kV-nɨŋ))
                                        (VP (VBP u-tus-u-kV-nɨŋ) (RB u-tus-u-kV-nɨŋ) (VP (VB loĩs-ma) (NP (NN loĩs-ma))))))))''')

        UCP = t[0]
        self.assertEqual(len(UCP), 2)
        UCP.merge(0,1)


        self.assertEqual(len(UCP), 1)
        self.assertEqual(len(UCP[0]), 4)

    def ctn_merge_2_test(self):
        src_t = IdTree.fromstring('''(ROOT
                                      (UCP
                                        (S
                                          (NP (PRP They))
                                          (VP
                                            (VBP are)
                                            (RB also)
                                            (ADJP
                                              (RB too)
                                              (JJ lazy)
                                              (S
                                                (VP
                                                  (TO to)
                                                  (VP (VB take) (NP (PRP it)) (ADVP (RB out,))))))))
                                        (CC and)
                                        (SBAR
                                          (IN so)
                                          (S
                                            (NP (PRP they))
                                            (VP (VBP do) (RB not) (VP (VB drink) (NP (NN it.))))))))''')
        tgt_w = RGWordTier.from_string('loĩs-ma yaŋ hunci-suma kat-a-ŋs-e kina u-tus-u-kV-nɨŋ')
        aln = Alignment([(16, 6), (3, 2), (7, 1), (15, 3), (9, 3), (11, 3), (12, 6), (14, 6), (13, 6), (4, 3), (5, 3)])

        proj = project_ps(src_t, tgt_w, aln)
        self.assertEqual(len(proj.leaves()), 6)


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

    def parse_test(self):
        dep_string =            ('''advmod(meet-3, When-1)
                                    nsubj(meet-3, we-2)
                                    xsubj(know-7, we-2)
                                    advmod(meet-3, let's-4)
                                    dep(meet-3, get-5)
                                    aux(know-7, to-6)
                                    xcomp(get-5, know-7)
                                    det(talk.-13, each-8)
                                    num(let's-10, other,-9)
                                    npadvmod(laugh,-11, let's-10)
                                    amod(talk.-13, laugh,-11)
                                    amod(talk.-13, let's-12)
                                    dobj(know-7, talk.-13)''')
        self.assertRaises(TreeError, DepTree.fromstring, dep_string)


class DepTreeCycleTest(unittest.TestCase):

    def test_cycle(self):
        dt_string = '''nsubj(did-2, And-1) root(ROOT-0, did-2) dobj(did-2, you-3) dep(did-2, make-4) dobj(make-4, rice-5) nsubj(day,-7, rice-5) rcmod(rice-5, day,-7) dep(did-2, eat-9) conj_and(make-4, eat-9) dobj(eat-9, it?-10)'''

        dt = DepTree.fromstring(dt_string)

        self.assertEqual(dt[0].label(), 'did')

class DepTreeParseTests(unittest.TestCase):
    def broken_parse_test(self):
        dt_string = '''nsubj(get-2, I-1) nsubj(get-2', I-1) conj_and(get-2, get-2') prt(get-2, up-3) prep_at(get-2, eight-5) dep(is-11, that-8) det(problem-10, the-9) nsubj(is-11, problem-10) xsubj(cook-13, problem-10) prepc_after(get-2', is-11) aux(cook-13, to-12) xcomp(is-11, cook-13) xcomp(is-11, eat-15) conj_and(cook-13, eat-15) dobj(cook-13, rice.-16)
                    '''
        self.assertRaises(TreeError, DepTree.fromstring, dt_string)

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