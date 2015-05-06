import re
from collections import defaultdict
from copy import copy
import itertools
import logging

from nltk.tree import ParentedTree, Tree


#===============================================================================
# Exceptions
#===============================================================================

class TreeError(Exception): pass
class PhraseTreeError(TreeError): pass

class TreeProjectionError(Exception): pass
class TreeMergeError(TreeProjectionError): pass

PS_LOG = logging.getLogger('PS_PROJECT')
DS_LOG = logging.getLogger('DS_PROJECT')



class IdTree(ParentedTree):
    """
    This is a tree that inherits from NLTK's tree implementation,
    but assigns IDs that can be used in writing out the Xigt format.
    """
    def __init__(self, node, children=None, id=None):
        super().__init__(node, children)
        self.id = id

    def __eq__(self, other):
        q = ParentedTree.__eq__(self, other)
        return q and (self.id == other.id)

    def similar(self, other):
        """
        Test equivalency in a tree, but without

        :param other:
        :return:
        """
        if not isinstance(other, Tree):
            return False
        if len(self) != len(other):
            return False
        for my_child, other_child in zip(self, other):
            if not my_child.similar(other_child):
                return False

        # If we make it all the way through without returning false,
        # return True.
        return True

    def assign_ids(self, id_base=''):
        """
        Assign IDs to the elements of the tree, using the "id_base" string
        as a leading element.
        |
        Example: `id_base` of `'ds'` would result in `'ds1'`, `'ds2'` etc.

        :param id_base: base which to build the IDs from
        :type id_base: str
        """

        # Per the conventions, we want the preterminals to start from one.
        i = 1
        for st in self.preterminals():
            st.id = '%s%d' % (id_base, i)
            i+=1

        for st in self.nonterminals():
            st.id = '%s%d' % (id_base, i)
            i+=1

    def find_start_index(self, idx):
        return self.find(lambda x: x.is_preterminal() and x.span()[0] == idx)

    def find_stop_index(self, idx):
        return self.find(lambda x: x.is_preterminal() and x.span()[1] == idx)

    def find_index(self, idx):
        return self.find(lambda x: x.is_preterminal() and x.span() == (idx,idx))

    def __hash__(self):
        return hash(self.label()) + hash(self.span()) + hash(self.id)

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

    def delete(self, propagate=True):
        """
        Delete self from parent.

         :param propagate: If true, then delete parents that are made empty by this deletion.
         :type propagate: bool
        """
        p = self.parent()
        del p[self.parent_index()]


        if propagate and p is not None and not p:
            p.delete(propagate)

    def replace(self, t):
        """
        Replace this node in its parent with t

        :param t: The tree to replace this instance with
        """

        p = self.parent()
        if p is None:
            raise TreeError('Attempt to replace a subtree "{}" with no parent.'.format(self))

        i = self.parent_index()
        self.delete(propagate=False)
        p.insert(i, t)

    def copy(self):
        """
        Perform a deep copy

        :rtype: IdTree
        """
        new_children = [t.copy() for t in self]
        return IdTree(self.label(), new_children, id=copy(self.id))

    @classmethod
    def fromstring(cls, tree_string, id_base=''):
        """
        :param tree_string:  String of a phrase structure tree in PTB format.
        :param id_base:
        :param kwargs:
        :rtype : IdTree
        """
        t = super(IdTree, cls).fromstring(tree_string,
                                          # When leaves are read in, make them Terminal objects.
                                        read_leaf=lambda x: Terminal(x))
        t.assign_ids()
        for i, leaf in enumerate(t.leaves()):
            leaf.index = i+1


        return t

    def preterminals(self):
        return self.subtrees(filter=lambda t: t.is_preterminal())

    def nonterminals(self):
        return self.subtrees(filter=lambda t: not t.is_preterminal())

    def is_preterminal(self):
        """
        Check whether or not the given node is a preterminal (its height
        should be == 2)
        """
        return self.height() == 2

    def indices_labels(self):
        """
        Iterate through the tree, and return the list of
        (label, head, child) tuples.
        """
        if self.parent():
            ret_tup = [(self.type, self.parent().word_index, self.word_index)]
        else:
            ret_tup = []

        for child in self:
            ret_tup += child.indices_labels()
        return ret_tup

    def lprint(self):
        return '{}[{}]'.format(self.label(), self.treeposition())

    def span(self, caller=None):
        """
        Return the span of indices covered by this node.
        """

        # 1) If we only have one child, then simply
        #    return the span of that child.
        if len(self) == 1:
            return self[0].span(caller=caller)

        # 2) Otherwise, return a span consisting of
        #    the (leftmost, rightmost) indices of the
        #    children.
        else:
            subspans = sorted(s.span(caller=caller) for s in self)
            if not subspans:
                raise TreeProjectionError('Dangling unary: {} - root = {}'.format(self, self.root()))
            return (subspans[0][0], subspans[-1][1])

    def promote(self):
        """
        Delete this node and promote its children
        """

        # Get the index of this node, and a ref
        # to its parent, then delete it.
        my_idx = self.parent_index()
        parent = self.parent()

        # Don't propagate deletion up through the parent before
        # we have re-added the children.
        assert self.parent(), self
        self.delete(propagate=False)

        # For each of that node's children,
        # remove their parent attribute
        # then re-add them to the parent
        # where the old node had been.
        for i, child in enumerate(self):
            child._parent = None
            parent.insert(my_idx+i, child)


    def swap(self, i, j):
        """
        Swap the node indices i and j.
        :param i:
        :type i: int
        :param j:
        :type j: int
        """

        assert i < j

        i_n = self[i]
        j_n = self[j]

        del self[i]
        del self[j-1]

        self.insert(i, j_n)
        self.insert(j, i_n)

    def merge(self, i, j, unify_children=True):
        """
        Merge the node indices i and j

        :param i:
        :type i: int
        :param j:
        :type j: int
        """

        if i == j:
            raise TreeMergeError("Indices cannot be equal in a merge.")

        # If we have a nonterminal that has the same span as a preterminal, we want
        # to take all of the preterminals underneath the nonterminal and combine them with
        # the preterminal, then delete the nonterminal.

        if (self[i].is_preterminal() != self[j].is_preterminal()):
            #TODO: revisit what happens here when merging a preterminal and a nonterminal...

            # Make a list of the preterminals that we are going to merge.
            preterms_to_merge = [preterm for preterm in list(self[i].preterminals())+list(self[j].preterminals())]

            # There should only be
            assert self[i].span()[1] - self[i].span()[0] == 0
            assert self[j].span()[1] - self[i].span()[0] == 0

            i_n = self[i] if self[i].is_preterminal() else []
            j_n = self[j] if self[j].is_preterminal() else []
            pt_n = i_n or j_n


            # Keep a list of the labels for the new preterm that will be joined by '+'
            labels = []

            del self[i]
            del self[j-1]

            # Create the label list.
            for preterm in preterms_to_merge:
                preterm._parent = None # Remove the parent so that it can be added.
                for label in preterm.label().split('+'):
                    if label not in labels:
                        labels.append(label)

            # Now, create the new preterminal.
            n = IdTree('+'.join(labels), pt_n, id=pt_n.id)


            self.insert(i, n)
            return






        assert i < j, 'i must be smaller index'

        i_n = self[i]
        j_n = self[j]

        del self[i]
        del self[j-1]


        new_children = []
        # Create the new node that is a "+" combination of
        # the labels, and just the child of the first.
        newlabel = i_n.label()+'+'+j_n.label()

        for child in i_n:
            if isinstance(child, Tree):
                child._parent = None
            new_children.append(child)

        for child in j_n:
            if isinstance(child, Tree):
                child._parent = None
            new_children.append(child)

        # In the preterminal sense we are usually merging terminals
        # that were originally the same word, with the same index,
        # so collapse the children to only one since it's a duplicate.
        if i_n.is_preterminal() and j_n.is_preterminal():
            new_children = new_children[0:1]
            assert len(new_children) == 1


        n = IdTree(newlabel, children=new_children, id=i_n.id)


        self.insert(i, n)

    def insert_by_span(self, t):

        assert not self.is_preterminal(), "Should not be preterminal"

        last_index = None
        for i, sibling in enumerate(self):
            sib_start, sib_stop = sibling.span()
            my_start, my_stop = t.span()
            if sib_start > my_start:
                last_index = i
                break

        last_index = last_index if last_index is not None else len(self)

        PS_LOG.debug('Inserting {} into {} at position {}'.format(t.pformat(margin=5000), self.pformat(margin=5000), last_index))
        PS_LOG.debug('Tree is now: {}'.format(self.root()))
        self.insert(last_index, t)

class Terminal(object):
    def __init__(self, label, index=None):
        self.label = label
        self.index = index
        if index is not None:
            self.index = int(index)

    def __str__(self):
        return self.label
    def __eq__(self, other):
        return isinstance(other, Terminal) and self.label == other.label and self.index == other.index
    def __repr__(self):
        return self.label
    def __len__(self):
        return len(self.label)
    def __hash__(self):
        return hash('{}[{}]'.format(self.label, self.index))

    def span(self, caller=None):
        return (self.index, self.index)

    def similar(self, other):
        return self.__eq__(other)

    def copy(self):
        return Terminal(copy(self.label), copy(self.index))


def build_tree(dict):
    """
    Since

    :param dict:
    :return:
    """
    root = Terminal('ROOT', index=0)
    return DepTree(root.label, _build_tree(dict, root), word_index=root.index)

def _build_tree(dict, word):
    if word not in dict:
        return []
    else:
        children = []
        for dep_type, child in dict[word]:
            d = DepTree(child.label, _build_tree(dict, child), type=dep_type, word_index=child.index)
            children.append(d)
        return children




def get_nodes(string):
    """

    :param string: A string representation of the dependency tree produced by the stanford parser.
    :return: Dictionary of
    :rtype: dict
    """
    nodes = re.findall('(\w+)\((.*?\d+)\)', string)

    # We are going to store a dictionary of words
    # and their children, and then construct the
    # tree from "ROOT" on down...
    child_dict = defaultdict(list)

    # Go through each of the returned values...
    for name, pair in nodes:
        head, child = re.split(',\s', pair)

        w_i_re = re.compile('(\S+)-(\d+)')

        head  = Terminal(*re.search(w_i_re, head).groups())
        child = Terminal(*re.search(w_i_re, child).groups())

        child_dict[head].append((name, child))

    return child_dict


def aln_indices(tokens):
    index_str = ''
    for i, token in enumerate(tokens):
        index_str += ('{:<' + str(len(token)+1) + '}').format(i+1)
    return index_str


def project_ps(src_t, tgt_w, aln):

    """
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
    """

    PS_LOG.debug('Projecting phrase structure.')
    PS_LOG.debug('             ' + aln_indices(src_t.leaves()))
    PS_LOG.debug('SRC        : %s' % ' '.join([str(l) for l in src_t.leaves()]))
    PS_LOG.debug('SRC -> TGT : %s' % str(sorted(list(aln))))
    PS_LOG.debug('TGT        : %s' % tgt_w.text())
    PS_LOG.debug('             ' + aln_indices([t.value() for t in tgt_w]))


    src_is = [x[0] for x in aln]

    # 1) Copy the English PS... ---
    tgt_t = src_t.copy()

    # 1b) Remove unaligned words... ---
    nodes_to_delete = []
    for pt in tgt_t.preterminals():
        if pt.span()[0] not in src_is:
            nodes_to_delete.append(pt)

    for n in nodes_to_delete:
        n.delete()


    # 2) Replace all the English words with the foreign words ---
    #    (and their indices!)
    aln = sorted(aln, key=lambda x: x[1])

    # If we swap the nodes immediately, then we won't be able to
    # search by index correctly. Let's build a dict of the new nodes
    # to replace the old ones with.
    nodes_to_replace = defaultdict(list)

    for src_i, tgt_i in aln:

        # Get the t for the new tree...
        tgt_n = tgt_t.find_index(src_i)

        # This must be a preterminal...
        assert(tgt_n.is_preterminal())

        # Get the correct word for the index...
        w = tgt_w.get_index(tgt_i)

        # Make an entry in the dictionary with the new
        # Preterminal/Terminal combination.
        tgt_n_copy = tgt_n.copy()
        tgt_n_copy[0] = Terminal(w.value(), index=w.index)

        nodes_to_replace[tgt_n].append(tgt_n_copy)


    # Now, let's do the swapping.
    for n, preterms in nodes_to_replace.items():

        # Find the node we are replacing, get its
        # index, and delete it.
        p = n.parent()
        i = n.parent_index()

        # Don't propagate the deletion, since we are replacing it...
        n.delete(propagate=False)

        # Now, add every node that aligned with this one
        # as siblings.
        for preterm in preterms:

            # From (Xia and Lewis, 2007):
            # "If an English word x aligns to several source words,
            # we will make several copies of the node for x, one
            # copy for each such source word. The copies will all
            # be siblings in the DS."

            PS_LOG.debug('Inserting {2:>14s} {3:<4s} in place of {0:<4s} {1:<14s}'.format('"%s"'%n, '[%s]'%str(n.span()), '[%d]'%preterm[0].index, '"%s"' % preterm[0].label))
            p.insert(i, preterm)


    PS_LOG.debug('Current Tree: {}'.format(tgt_t.pformat(margin=100)))

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

        assert left_words or right_words, "No aligned words were found..."

        left_word = None if not left_words else left_words[-1]
        right_word= None if not right_words else right_words[0]

        # Create the new preterminal node with the label 'UNK',
        # using the ID label provided by this word, and its index
        # at the preterminal stage.
        t = IdTree('UNK', [Terminal(unaligned_tgt_word.value(), index=unaligned_tgt_word.index)], id=unaligned_tgt_word.id)


        # If the only aligned word found was to the right,
        # select the preterminal with a span that starts
        # at that right word's index.
        if not left_word:
            left_n = tgt_t.find_start_index(right_word.index)
            left_n.parent().insert_by_span(t)

        # If the only aligned word found was to the left,
        # select the preterminal with a span that ends
        # at that left word's index
        elif not right_word:
            right_n = tgt_t.find_stop_index(left_word.index)
            right_n.parent().insert_by_span(t)

        else:
            left_n = tgt_t.find_stop_index(left_word.index)
            right_n= tgt_t.find_start_index(right_word.index)

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


# Contained items function
def contains(t, s_sup, s_sub):
    PS_LOG.debug('{} {} is contained in {} {}'.format(s_sub.label(), s_sub.span(), s_sup.label(), s_sup.span()))
    # PS_LOG.debug('{}'.format(s_sub.root()))
    # PS_LOG.debug('{}'.format(s_sup.root()))
    PS_LOG.debug('PROMOTE: {} [{}] into {}'.format(s_sub, s_sub.span(), s_sup))
    s_sup.promote()
    assert s_sup.parent() == None
    PS_LOG.debug('TREE is now: {}'.format(t.root()))

def reorder_tree(t, prev_t_list = []):
    """
    Recursively reorder a tree.

    :param t:
    :type t:
    """


    was_changed = False

    prev_t = t.root().copy()

    if not t.is_preterminal():
        if len(t) == 1:
            PS_LOG.debug('Unary node {}[{}], skipping.'.format(t.label(), t.span(caller=t)))

        elif len(t) >= 2:

            # Try each combination pairwise...
            for s_i, s_j in itertools.combinations(t, 2):
                a_i, b_i = s_i.span()
                a_j, b_j = s_j.span()

                # TODO: FIXME: How is it that the parent pointers get corrupted?
                s_i._parent = t
                s_j._parent = t

                s_i_idx = s_i.parent_index()
                s_j_idx = s_j.parent_index()

                # 3a) The nodes are already in order and do not overlap. Do nothing. ---
                if b_i < a_j:
                    #PS_LOG.debug('Nothing to be done for {}[{}] and {}[{}]'.format(s_i.label(), s_i.span(), s_j.label(), s_j.span()))
                    pass

                # 3b) The nodes are swapped. ---
                elif a_i > a_j and b_i > b_j:
                    PS_LOG.debug('SWAPPING: {:>30} [{},{}] for [{},{}] {:<12}'.format(str(s_i), a_i, b_i, a_j, b_j, str(s_j)))
                    t.swap(s_i_idx, s_j_idx)
                    was_changed = 'SWAPPED'
                    break

                # 3c-i) S_i contains S_j              ---
                # delete s_i and promote its children.
                elif a_i < a_j and b_i > b_j:
                    contains(t, s_i, s_j)
                    was_changed = 'PROMOTED {} into {}'.format(s_j, s_i)
                    break

                # 3c-ii) S_j is contained by S_i ---
                #  delete s_j and promote its children.
                elif a_i > a_j and b_i < b_j:
                    was_changed = 'T WAS: {} \n\n PROMOTED {} into {}'.format(t.root(), s_i.lprint(), s_j.lprint())
                    contains(t, s_j, s_i)
                    was_changed += ' to become\n\n {}'.format(t.root())
                    break

                # d) S_j and S_i overlap but are not subsets. ---


                # 3di) They are the same span. ---
                #    Merge them
                elif a_i == a_j and b_i == b_j:
                    PS_LOG.debug('Merging: {:>30} [{},{}] with [{},{}] {:<}'.format(str(s_i), a_i, b_i, a_j, b_j, str(s_j)))
                    t.merge(s_i_idx, s_j_idx)
                    PS_LOG.debug('New tree:\n{}'.format(t.root()))
                    was_changed = 'MERGED {} and {}'.format(s_i, s_j)
                    break

                # 3dii) They are different ---
                # Promote both of them.
                else:
                    PS_LOG.debug('Non-exclusive overlap')
                    for s in [s_i, s_j]:
                        if not s.is_preterminal():
                            PS_LOG.debug('Promoting {}[{}]'.format(s_i.label(), s_i.span()))
                            s.promote()

                    PS_LOG.debug('New tree:\n{}'.format(t.root()))
                    was_changed = 'Promoted {} and {}'.format(s_i, s_j)
                    break

        # If we changed somewhere along the way, let's try again from the top first.
        if was_changed:
            prev_t_list.append(prev_t)
            reorder_tree(t.root(), prev_t_list)
            return t.root()

        # Otherwise, this node does not require changes, but let's
        # recurse down it's children.
        else:
            for child in t:

                changed_tree = reorder_tree(child, prev_t_list)

                if changed_tree:
                    ct = reorder_tree(changed_tree, prev_t_list)
                    return ct



class DepTree(IdTree):

    def __init__(self, node, children=None, id=None, type=None, word_index=None):
        super().__init__(node, children, id)
        self.type = type
        self._word_index = word_index

    @classmethod
    def fromstring(cls, tree_string, id_base='', **kwargs):
        """
        Read a dependency tree from the stanford dependency format. Example:

        ::

            nsubj(ran-2, John-1)
            root(ROOT-0, ran-2)
            det(woods-5, the-4)
            prep_into(ran-2, woods-5)

        :param tree_string: String to parse
        :type tree_string: str
        :param id_base: ID string on which to base the IDs in this tree.
        :type id_base: str
        """
        DS_LOG.debug('Building dependency tree from: {}'.format(tree_string))


        child_dict = get_nodes(tree_string)
        t = build_tree(child_dict)
        t.assign_ids(id_base)
        return t

    @property
    def word_index(self):
        return self._word_index

    def __str__(self):
        ret_str = '(%s[%s]' % (self.label(), self.word_index)
        for child in self:
            ret_str += ' %s' % str(child)
        return ret_str + ')'

    def find_index(self, idx):
        return self.find(lambda x: x.word_index == idx)

    def __eq__(self, other):
        if (self.word_index != other.word_index):
            return False
        elif (self.type != other.type):
            return False
        elif len(self) != len(other):
            return False
        elif (self._label != other._label):
            return False
        for my_child, their_child in zip(self, other):
            if not my_child == their_child:
                return False
        return True

    def span(self):
        raise TreeError('Span is not supported for dependency tree.')

    def copy(self):
        children = [c.copy() for c in self]
        dt = DepTree(copy(self.label()), children, id=copy(self.id), type=copy(self.type), word_index=copy(self.word_index))
        return dt
