
from nltk.tree import ParentedTree, Tree
import re
from collections import defaultdict
import sys
import unittest
import intent.alignment.Alignment
from copy import copy
import itertools
import logging

#===============================================================================
# Exceptions
#===============================================================================

class TreeError(Exception): pass
class PhraseTreeError(TreeError): pass

class TreeProjectionError(Exception): pass
class TreeMergeError(TreeProjectionError): pass

PS_LOG = logging.getLogger('PS_PROJECT')

class IdTree(ParentedTree):
    '''
    This is a tree that inherits from NLTK's tree implementation,
    but assigns IDs that can be used in writing out the Xigt format.
    '''
    def __init__(self, node, children=None, id=None, index=None):
        super().__init__(node, children)
        self.id = id
        self.index = index

    def __eq__(self, other):
        q = ParentedTree.__eq__(self, other)
        return q and (self.id == other.id) and (self.index == other.index)


    def assign_ids(self, id_base=''):
        '''
        Assign IDs to the elements of the tree, using the "id_base" string
        as a leading element.
        |
        Example: `id_base` of `'ds'` would result in `'ds1'`, `'ds2'` etc.

        :param id_base: base which to build the IDs from
        :type id_base: str
        '''

        # Per the conventions, we want the preterminals to start from one.
        i = 1
        for st in self.preterminals():
            st.id = '%s%d' % (id_base, i)
            i+=1

        for st in self.nonterminals():
            st.id = '%s%d' % (id_base, i)
            i+=1

    def find_index(self, idx):
        return self.find(lambda x: x.index == idx)

    def find(self, filter):

        # Must search by either id or index
        if filter(self):
            return self

        elif self.is_preterminal():
            return None
        else:
            ret = None
            for child in self:
                found = child.find(filter)
                if found is not None:
                    ret = found
                    break
            return ret


    def delete(self):
        '''
        Delete self from parent.
        '''
        del self.parent()[self.parent_index()]


    def copy(self):
        '''
        Perform a deep copy

        :rtype: IdTree
        '''
        if self.is_preterminal():
            return IdTree(self.label(), copy(self), id=self.id, index=self.index)
        else:
            new_children = [t.copy() for t in self]
            return IdTree(self.label(), new_children, id=self.id, index=self.index)

    @classmethod
    def fromstring(cls, s, id_base='', **kwargs):
        t = super(IdTree, cls).fromstring(s, **kwargs)
        t.assign_ids()
        for i, pt in enumerate(t.preterminals()):
            pt.index = i+1
        return t

    def preterminals(self):
        return self.subtrees(filter=lambda t: t.is_preterminal())

    def nonterminals(self):
        return self.subtrees(filter=lambda t: not t.is_preterminal())

    def is_preterminal(self):
        '''
        Check whether or not the given node is a preterminal (its height
        should be == 2)
        '''
        return self.height() == 2

    def indices_labels(self):
        '''
        Iterate through the tree, and return the list of
        (label, head, child) tuples.
        '''
        if self.parent():
            ret_tup = [(self.type, self.parent().index, self.index)]
        else:
            ret_tup = []

        for child in self:
            ret_tup += child.indices_labels()
        return ret_tup



    def span(self):
        '''
        Return the span of indices covered by this node.
        '''

        # 1) If this node is a preterminal, just return
        #    the (1,1) pair of indices for this node.

        if self.is_preterminal():
            return (self.index, self.index)

        # 2) If we only have one child, then simply
        #    return the span of that child.
        elif len(self) == 1:
            return self[0].span()

        # 3) Otherwise, return a span consisting of
        #    the (leftmost, rightmost) indices of the
        #    children.
        else:
            return (self[0].span()[0], self[-1].span()[1])

    def promote(self):
        '''
        Delete this node and promote its children
        '''

        # Get the index of this node, and a ref
        # to its parent, then delete it.
        my_idx = self.parent_index()
        parent = self.parent()
        self.delete()

        # For each of that node's children,
        # remove their parent attribute
        # then re-add them to the parent
        # where the old node had been.
        for i, child in enumerate(self):
            child._parent = None
            parent.insert(my_idx+i, child)

    def swap(self, i, j):
        '''
        Swap the node indices i and j.
        :param i:
        :type i: int
        :param j:
        :type j: int
        '''

        assert i < j

        i_n = self[i]
        j_n = self[j]


        del self[i]
        del self[j-1]


        self.insert(i, j_n)
        self.insert(j, i_n)


    def merge(self, i, j):
        '''
        Merge the node indices i and j

        :param i:
        :type i: int
        :param j:
        :type j: int
        '''

        if i == j:
            raise TreeMergeError("Indices cannot be equal in a merge.")


        assert i < j, 'i must be smaller index'

        i_n = self[i]
        j_n = self[j]

        del self[i]
        del self[j-1]

        # Create the new node that is a "+" combination of
        # the labels, and just the child of the first.
        newlabel = '{}+{}'.format(i_n.label(), j_n.label())
        for child in i_n:
            if isinstance(child, Tree):
                child._parent = None

        n = IdTree(newlabel, list(i_n), index=i_n.index, id=i_n.id)


        self.insert(i, n)



    def insert_by_span(self, t):

        assert not self.is_preterminal(), "Should not be preterminal"

        last_index = None
        for i, sibling in enumerate(self):
            start, stop = sibling.span()
            if start > t.index:
                last_index = i
                break

        last_index = last_index if last_index is not None else len(self)

        PS_LOG.debug('Inserting {} into {} at position {}'.format(t.pprint(margin=5000), self.pprint(margin=5000), last_index))
        self.insert(last_index, t)



class Word(object):
    def __init__(self, w, i):
        self.w = w
        self.i = int(i)

    def __str__(self):
        return self.w
    def __repr__(self):
        return self.w
    def __hash__(self):
        return hash(self.w)
    def __eq__(self, o):
        return self.w == str(o)

def build_tree(dict):
    return DepTree('ROOT', _build_tree(dict, 'ROOT'))

def _build_tree(dict, word):
    if word not in dict:
        return []
    else:
        children = []
        for dep_type, child in dict[word]:
            d = DepTree(child.w, _build_tree(dict, child), type=dep_type, index=child.i)
            children.append(d)
        return children




def get_nodes(string):
    nodes = re.findall('(\w+)\((.*?)\)', string)

    # We are going to store a dictionary of words
    # and their children, and then construct the
    # tree from "ROOT" on down...
    child_dict = defaultdict(list)

    # Go through each of the returned values...
    for name, pair in nodes:
        head, child = pair.split(',')

        w_i_re = re.compile('(\S+)-([0-9]+)')

        head  = Word(*re.search(w_i_re, head).groups())
        child = Word(*re.search(w_i_re, child).groups())

        child_dict[head].append((name, child))

    # Now that we have the dictionary, we can start from "ROOT"
    return build_tree(child_dict)

def aln_indices(tokens):
    index_str = ''
    for i, token in enumerate(tokens):
        index_str += ('{:<' + str(len(token)+1) + '}').format(i+1)
    return index_str


def project_ps(src_t, tgt_w, aln):

    '''
    1. Copy the English PS, and remove all unaligned English words.

    2. Replace each English word with the corresponding target words.

        * If an English word x aligns to several target words, \
        make copies of the t, one copy for each such word. The copies will all be siblings.

    3. Start from the root of the projected	PS and for each \
    t x with more than one child, reorder each pair \
    of x's children until they are in the correct order.

        * Let y_i and y_j be two children of x
        * Spans are:
            * S_i = [a_i,b_i]
            * S_j = [a_j,b_j]
        * Reordering y_i and y_j gives four scenarios:
            * S_i and S_j don't overlap.
                * Put y_i before y_j if a_i < a_j
                * Put y_i after  y_j if a_i > a_j
                * S_i is contained within S_j
                    * Remove y_i and promote its children

                * S_j is contained with S_i
                    * Remove y_j and promote its children

                * S_i and S_j overlap, but neither contains
                  the other.
                    * Remove both, promote their children
                    * If they are both leaf nodes with the
                    * Same span, merge them. (IN+DT, for example)

    4. Reattach unaligned words.
        * For each unaligned word x:
            * Find closest left and right aligned neighbor
            * Attach x to the lowest common ancestor of the two.
    '''

    PS_LOG.debug('Projecting phrase structure.')
    PS_LOG.debug('             ' + aln_indices(src_t.leaves()))
    PS_LOG.debug('SRC        : %s' % ' '.join(src_t.leaves()))
    PS_LOG.debug('SRC -> TGT : %s' % str(sorted(list(aln))))
    PS_LOG.debug('TGT        : %s' % tgt_w.text())
    PS_LOG.debug('             ' + aln_indices([t.get_content() for t in tgt_w]))


    src_is = [x[0] for x in aln]

    # 1) Copy the English PS... ---
    tgt_t = src_t.copy()

    # 1b) Remove unaligned words... ---
    nodes_to_delete = []
    for pt in tgt_t.preterminals():
        if pt.index not in src_is:
            nodes_to_delete.append(pt)

    for n in nodes_to_delete:
        n.delete()


    # 2) Replace all the English words with the foreign words ---
    #    (and their indices!)
    aln = sorted(aln, key=lambda x: x[1])

    # If we swap the nodes immediately, then we won't be able to
    # search by index correctly, so let's compile a list and then
    # do the swap.
    nodes_to_swap = []


    for src_i, tgt_i in aln:

        # Get the t for the new tree...
        tgt_n = tgt_t.find_index(src_i)

        # This must be a preterminal...
        assert(tgt_n.is_preterminal())

        # Get the correct word for the index...
        w = tgt_w.get_index(tgt_i)

        nodes_to_swap.append((tgt_n, w))

    # Now, let's do the swapping.
    for node, word in nodes_to_swap:
        PS_LOG.debug('Replacing {:>14s} {:<4s} with {:<4s} {:<14s}'.format('"%s"'%node[0], '[%d]'%node.index, '[%d]'%word.index, '"%s"' % word.get_content()))
        node[0] = word.get_content()
        node.index = word.index

    PS_LOG.debug('Current Tree: {}'.format(tgt_t.pprint(margin=100)))

    # 3) Reorder the tree...
    PS_LOG.debug('#'*10+' Now reordering tree...' + '#'*10)
    reorder_tree(tgt_t)


    # 4) Time to reattach unattached tgt words. ---
    PS_LOG.debug('#'*10+' Now reattaching unaligned words...' + '#'*10)
    aligned_indices = [t for s, t in aln]

    unaligned_tgt_words = [w for w in tgt_w if w.index not in aligned_indices]


    for unaligned_tgt_word in unaligned_tgt_words:

        # Get the left and right words that are aligned...
        left_words = [w for w in tgt_w if w.index < unaligned_tgt_word.index and w.index in aligned_indices]
        right_words= [w for w in tgt_w if w.index > unaligned_tgt_word.index and w.index in aligned_indices]

        assert left_words or right_words, "At least some words should alig..."

        left_word = None if not left_words else left_words[-1]
        right_word= None if not right_words else right_words[0]

        assert right_word or left_word

        t = IdTree('UNK', [unaligned_tgt_word.get_content()], id=unaligned_tgt_word.id, index=unaligned_tgt_word.index)


        # If there's only the right word, attach to that.
        if not left_word:
            left_n = tgt_t.find_index(right_word.index)
            left_n.parent().insert_by_span(t)

        # If there's only the left word, attach to that.
        elif not right_word:
            right_n = tgt_t.find_index(left_word.index)
            right_n.parent().insert_by_span(t)

        # TODO: What if there is both a left and a right.
        else:
            left_n = tgt_t.find_index(left_word.index)
            right_n= tgt_t.find_index(right_word.index)

            # Get the list of ancestors going up to the root of the
            # tree. The first point at which they "intersect"
            # is the point we want.
            left_ancestors = get_ancestors(left_n)
            right_ancestors = get_ancestors(right_n)

            lowest_ancestor = None

            for left_ancestor in left_ancestors:

                for right_ancestor in right_ancestors:
                    if left_ancestor == right_ancestor:
                        lowest_ancestor = left_ancestor
                        break

                if lowest_ancestor is not None:
                    break

            lowest_ancestor.insert_by_span(t)


    return tgt_t



def get_ancestors(t):
    return _get_ancestors(t.parent())

def _get_ancestors(t):
    if t is None:
        return []
    else:
        return [t]+_get_ancestors(t.parent())


def lowest_common_ancestor(t1, t2):

    t1_ancestors = None




def reorder_tree(t):
    '''
    Recursively reorder a tree.

    :param t:
    :type t:
    '''

    if not t.is_preterminal():
        if len(t) >= 2:

            # Try each combination pairwise...
            for s_i, s_j in itertools.combinations(t, 2):
                a_i, b_i = s_i.span()
                a_j, b_j = s_j.span()


                s_i_idx = s_i.parent_index()
                s_j_idx = s_j.parent_index()

                # 3a) The nodes are already in order. Do nothing. ---
                if a_i < a_j and b_i < b_j:
                    pass

                # 3b) The nodes are swapped. ---
                elif a_i > a_j and b_i > b_j:
                    PS_LOG.debug('SWAPPING: {:>30} [{},{}] for [{},{}] {:<12}'.format(str(s_i), a_i, b_i, a_j, b_j, str(s_j)))
                    t.swap(s_i_idx, s_j_idx)
                    # TODO: Write a testcase for swap
                    reorder_tree(t.root())
                    return


                # 3c-i) S_i contains S_j              ---
                # delete s_i and promote its children.
                elif a_i < a_j and b_i > b_j:
                    PS_LOG.debug('PROMOTE: {} [{},{}]'.format(s_i, b_i, b_j))
                    s_i.promote()
                    reorder_tree(t.root())
                    return


                # 3c-ii) S_j contains S_i ---
                #  delete s_j and promote its children.
                elif a_i > a_j and b_i < b_j:
                    PS_LOG.debug('PROMOTE: {} [{},{}]'.format(s_i, b_i, b_j))
                    s_j.promote()
                    reorder_tree(t.root())
                    return

                # d) S_j and S_i overlap but are not subsets. ---


                # 3di) They are the same span. ---
                #    Merge them
                elif a_i == a_j and b_i == b_j:
                    PS_LOG.debug('Merging: {:>30} [{},{}] with [{},{}] {:<}'.format(str(s_i), a_i, b_i, a_j, b_j, str(s_j)))
                    t.merge(s_i_idx, s_j_idx)
                    reorder_tree(t.root())
                    return

                    # TODO: Write a test case for merge

                # 3dii) They are different ---
                # Promote both of them.
                else:
                    if not s_i.is_preterminal():
                        s_i.promote()
                    if not s_j.is_preterminal():
                        s_j.promote()

                    reorder_tree(t.root())
                    return

        # If we've got to this point, that means that all of this node's children
        # are in order. Now, if this is a nonterminal, recurse down the children.
        for child in t:
            reorder_tree(child)

class DepTree(IdTree):

    def __init__(self, node, children=None, id=None, type=None, index=0):
        super().__init__(node, children, id, index)
        self.type = type

    @classmethod
    def fromstring(cls, s, id_base='', **kwargs):
        '''
        Read a dependency tree from the stanford dependency format. Example:

        ::

            nsubj(ran-2, John-1)
            root(ROOT-0, ran-2)
            det(woods-5, the-4)
            prep_into(ran-2, woods-5)

        :param s: String to parse
        :type s: str
        :param id_base: ID string on which to base the IDs in this tree.
        :type id_base: str
        '''

        t = get_nodes(s)
        t.assign_ids(id_base)
        return t

    def __str__(self):
        ret_str = '(%s[%s]' % (self.label(), self.index)
        for child in self:
            ret_str += ' %s' % str(child)
        return ret_str + ')'

class SpanTest(unittest.TestCase):

    def setUp(self):
        self.t = IdTree.fromstring('''(ROOT
  (SBARQ
    (WHNP (WP Who))
    (SQ (VBP do) (NP (PRP you)) (VP (VB believe) (VP (VBN called))))))'''
    )

    def test_span(self):
        self.assertEqual(self.t.span(), (1,5))

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

    def test_proj(self):
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
        t3idx = t3n.index

        t3n.id = 'asdf'

        self.assertNotEqual(self.t, t3)

        # Change it back.
        t3n.id = t3id
        self.assertEqual(self.t, t3)

        # Change the index
        t3n.index = -1
        self.assertNotEqual(self.t, t3)

        # Change it back
        t3n.index = t3idx
        self.assertEqual(self.t, t3)

    def test_promote(self):
        t2 = self.t.copy()
        t3 = self.t.copy()
        vp = self.t[1]
        vp.promote()

        self.assertNotEqual(self.t, t2)
        self.assertEqual(t2, t3)


from intent.igt.rgxigt import RGWordTier