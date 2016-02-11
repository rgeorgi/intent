import itertools
import logging
import re
from collections import defaultdict
from copy import copy

from nltk.tree import ParentedTree, Tree

from intent.alignment.Alignment import Alignment
#===============================================================================
# Constants / Strings
#===============================================================================
from intent.consts import punc_re_mult, PUNC_TAG, all_punc_re_mult
from intent.igt.igtutils import clean_lang_token
from intent.igt.references import item_index
from intent.corpora.conll import ConllSentence, ConllWord

DEPSTR_STANFORD = 'stanford'
DEPSTR_CONLL    = 'conll'
DEPSTR_PTB      = 'ptb-like'

#===============================================================================
# Exceptions
#===============================================================================
from intent.utils.token import POSToken


class TreeError(Exception): pass
class PhraseTreeError(TreeError): pass

class TreeProjectionError(Exception): pass
class TreeMergeError(TreeProjectionError): pass
class DepTreeProjectionError(TreeProjectionError): pass
class NoAlignmentProvidedError(TreeProjectionError): pass

PS_LOG = logging.getLogger('PS_PROJECT')
DS_LOG = logging.getLogger('DS_PROJECT')


class IdTree(ParentedTree):
    """
    This is a tree that inherits from NLTK's tree implementation,
    but assigns IDs that can be used in writing out the Xigt format.
    """
    def __init__(self, label, children=None, id=None):
        super().__init__(label, children)
        self.id = id

    def __eq__(self, other):
        q = ParentedTree.__eq__(self, other)
        return q and (self.id == other.id)

    def depth(self):
        if self.parent() is None:
            return 0
        else:
            return self.parent().depth() + 1

    def similar(self, other):
        """
        Test equivalency in a tree, but without labels

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

        else:
            ret = None
            for child in self:
                # Skip terminals
                if isinstance(child, Terminal):
                    continue

                found = child.find(filter)
                if found is not None:
                    ret = found
                    break
            return ret


    def findall(self, filter):
        found = []

        if filter(self):
            found += [self]

        for child in self:
            if not isinstance(child, Terminal):
                found += child.findall(filter)

        return found


    def delete(self, propagate=True, promote=False):
        """
        Delete self from parent.

         :param propagate: If true, then delete parents that are made empty by this deletion.
         :type propagate: bool
         :param promote: If true, then promote the children of this node to be children of the parent.
         :type promote: bool
        """
        p = self.parent()
        pi = self.parent_index()

        if p:
            del p[pi]

            # Promote the children of the deleted node if asked.
            if len(self) != 0 and promote:
                for offset, child in enumerate(self):
                    child._parent = None
                    p.insert(pi+offset, child)


            if propagate and p is not None and not p:
                p.delete(propagate)

    def insert_sibling(self, t):
        self.parent().insert(self.parent_index(), t)

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
    def fromstring(cls, tree_string, id_base='', **kwargs):
        """
        :param tree_string:  String of a phrase structure tree in PTB format.
        :param id_base:
        :param kwargs:
        :rtype : IdTree
        """
        t = super(IdTree, cls).fromstring(tree_string,
                                          # When leaves are read in, make them Terminal objects.
                                        read_leaf=lambda x: Terminal(x), **kwargs)
        t.assign_ids()
        for i, leaf in enumerate(t.leaves()):
            leaf.index = i+1

        return t

    def preterminals(self):
        return self.subtrees(filter=lambda t: t.is_preterminal())

    def nonterminals(self):
        return self.subtrees(filter=lambda t: not t.is_preterminal())

    def tagged_words(self):
        return [POSToken(pt[0].label, label=pt.label()) for pt in self.preterminals()]

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

    def spanlength(self):
        s = self.span()
        return s[1] - s[0]

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

            # Set the children based on unify_children
            if unify_children:
                children = pt_n
            else:
                children = []
                for pt in preterms_to_merge:
                    children += list(pt)

            # Now, create the new preterminal.
            n = IdTree('+'.join(labels), children, id=pt_n.id)


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
        if i_n.is_preterminal() and j_n.is_preterminal() and unify_children:
            new_children = new_children[0:1]
            assert len(new_children) == 1


        n = IdTree(newlabel, children=new_children, id=i_n.id)


        self.insert(i, n)

    def ancestors(self):
        """

        :rtype : list[DepTree]
        """
        if self.parent() is not None:
            return [self.parent()] + self.parent().ancestors()
        else:
            return []

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






def aln_indices(tokens):
    index_str = ''
    for i, token in enumerate(tokens):
        index_str += ('{:<' + str(len(token)+1) + '}').format(i+1)
    return index_str

def project_ds(src_t, tgt_w, aln):
    """
    1. Our DS projection algorithm is similar to the projection algorithms
        described in (Hwa et al. 2002) and (Quirk et al. 2005).

        It has four steps:

            1. Copy the English DS. and remove all the unaligned English words
            from the DS.

            2. We replace each English word in the DS with the corresponding
            source words. If an English word x aligns to several source words,
            we will make several copies of the node for x, one copy for each
            such source word. The copies will all be siblings in the DS.
            If a source word aligns to multiple English words, after Step 2
            the source word will have several copies in the resulting DS.

            3. In the third step, we keep only the copy that is closest
            to the root and remove all the other copies.

            4. In Step 4, we attach unaligned source words to the DS
            using the heuristics described in (Quirk et al. 2005).


    :param src_t: Source (English) tree to project from
    :type src_t: DepTree
    :param tgt_w: Set of target (non-English) words to use for projection
    :type tgt_w: RGWordTier
    :param aln: list of [(src, tgt)] index pairs (src == English)
    :type aln: Alignment
    """

    if not aln:
        raise NoAlignmentProvidedError("No alignment was provided. Cannot project.")

    # --1a) Start by copying the DS
    tgt_t = src_t.copy()

    # --1b) Get the unaligned nodes that we will be deleting later
    unaligned_eng_nodes = [n for n in tgt_t.subtrees(filter=lambda x: x.word_index not in aln.all_src())]

    # --1c) Delete all the unaligned nodes.
    for unaligned_node in unaligned_eng_nodes:
        DS_LOG.debug("Deleting unaligned English node: {}".format(unaligned_node))
        unaligned_node.delete()

    DS_LOG.debug("New tree: {}".format(tgt_t))

    # --2) Now, create a list of the nodes that need replacing.
    indices_to_replace = defaultdict(list)

    # Now, let's go through the aligned indices in order to replace
    # aligned nodes with their foreign language equivalents...
    for src_i, tgt_i in aln:

        # First, we find the source (English) nodes
        # (This is plural because we CAN have the same word listed twice...)
        src_nodes = tgt_t.findall_indices(src_i)

        for src_node in src_nodes:
            # Now, let's create a new node with the old
            # type, but new index and label
            tgt_word = tgt_w[tgt_i - 1]
            tgt_node = DepTree(tgt_word.value(), [], word_index = tgt_i, type=src_node.type)

            # Finally, let's append these new nodes to the list
            # associated with the old node (the list ensures
            # that any multiple alignments will be created
            # correctly as siblings.)
            indices_to_replace[src_node].append(tgt_node)

    # Now, let's go through the nodes to replace, and
    for node_to_replace in indices_to_replace.keys():
        # Get a list of the siblings we're going to replace
        # the original node with
        siblings = indices_to_replace[node_to_replace]

        # Now, insert them as siblings.
        for tgt_node in siblings:
            node_to_replace.insert_sibling(tgt_node)
            DS_LOG.debug('Inserting "{}[{}]" in place of "{}[{}]"'.format(tgt_node.label(),
                                                            tgt_node.word_index,
                                                            node_to_replace.label(),
                                                            node_to_replace.word_index))


        # Next, move the children of the original node
        # to be children of the first of the siblings.
        for child in node_to_replace:
            child._parent = None
            siblings[0].append(child)
            # DS_LOG.debug('Child "{}" of "{}" moved to "{}"'.format(child.label(),
            #                                                        node_to_replace.label(),
            #                                                        siblings[0].label()))

        # Finally, delete the old node (and don't promote children)
        node_to_replace.delete(promote=False)


    # --3) Now, for multiply-aligned words, only keep
    #      the shallowest one.
    multiply_aligned_indices = set([tgt_i for src_i, tgt_i in aln if len(aln.tgt_to_src(tgt_i)) > 1])
    for multiply_aligned_index in multiply_aligned_indices:

        # Find all the nodes with the given index, and sort
        # them by their depth.
        nodes = tgt_t.findall_indices(multiply_aligned_index)
        depth_sorted = sorted(nodes, key=lambda x: x.depth())

        # Now, delete all but the shallowest.
        for node in depth_sorted[1:]:
            node.delete()

    cur_nodes = tgt_t.subtrees()
    cur_indices = [st.word_index for st in cur_nodes]

    # --4) Now, reattach unaligned words...
    unaligned_tgt_indices = [item_index(w) for w in tgt_w if item_index(w) not in cur_indices]

    # Unaligned attachment from Quirk, et. al, 2005:
    #
    # Unaligned target words are attached into the dependency
    # structure as follows: assume there is an unaligned word
    # t_j in position j. Let i < j and k > j be the target positions
    # closest to j such that t_i depends on t_k or vice versa:
    # attach t_j to the lower of t_i or t_k.
    #
    # If all the nodes to the left (or right) of position j are
    # unaligned, attach tj to the left-most (or right-most)
    # word that is aligned.

    attachments_to_make = []

    if unaligned_tgt_indices:
        DS_LOG.debug("Reattaching unaligned target indices...".format(unaligned_tgt_indices))

    for j in unaligned_tgt_indices:
        # DS_LOG.debug("Attempting to reattach unaligned word: {}[{}]".format(tgt_w.get_index(j).value(), j))

        left_indices  = sorted([i for i in aln.all_tgt() if i < j])
        right_indices = sorted([k for k in aln.all_tgt() if k > j])

        # Convert the tree representation to a list of (head, child) indices
        indices = tgt_t.to_indices()

        # Filter the indices such that only those where j is in between the
        # two.
        indices = [(i, k) for i, k in indices if (i < j < k) or (k < j < i)]

        # Now, sort these indices by their closeness to the current index
        indices.sort(key=lambda x: abs(j - x[0]) + abs(j - x[1]))

        # If there are no indices to the left, attach to the leftmost of those
        # to the right...
        if not left_indices and right_indices:
            attachments_to_make.append((j, right_indices[0]))

        # If there are no indices to the right, attach to the rightmost of those
        # to the left...
        elif not right_indices and left_indices:
            attachments_to_make.append((j, left_indices[-1]))

        # If we have indices to the left and right, find whether one depends
        # on the other...
        elif indices:
            # And, finally, queue the unaligned node to attach to the "lower"
            # (child) of the index pair.
            attachments_to_make.append((j, indices[0][1]))

        else:
            DS_LOG.warning('Unable to reattach index "{}"'.format(j))





    for unaln_i, aln_i in attachments_to_make:
        tgt_word = tgt_w[unaln_i - 1].value()
        aln_node = tgt_t.find_index(aln_i)

        #TODO: Determine why we're not occasionally not finding the unaligned nodes?
        if aln_node is not None:
            unaln_node = DepTree(tgt_word, [], word_index=unaln_i)

            DS_LOG.debug("Attaching {}[{}] to {}[{}]".format(tgt_word, unaln_i,
                                                             aln_node.label(), aln_i))

            aln_node.append(unaln_node)

    # Finally, just go through and make sure the children are sorted by index.
    seen_edges = set([])

    for st in list(tgt_t.subtrees()):
        st.sort(key=lambda x: x.word_index)

        # And do one more check... we should allow the same word to appear multiple times
        # in the tree, but not as its own sibling.
        edge = None if st.parent() is None else (st.word_index, st.parent().word_index)

        if edge not in seen_edges:
            seen_edges.add((st.word_index, st.parent().word_index))
        else:
            st.delete(promote=False)

    # print(tgt_t.to_indices())

    return tgt_t




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

    if len(aln) == 0:
        raise NoAlignmentProvidedError("No aligned words found, cannot project.")


    PS_LOG.debug('Projecting phrase structure.')
    PS_LOG.debug('             ' + aln_indices(src_t.leaves()))
    PS_LOG.debug('SRC        : %s' % ' '.join([str(l) for l in src_t.leaves()]))
    PS_LOG.debug('SRC -> TGT : %s' % str(sorted(list(aln))))
    PS_LOG.debug('TGT        : %s' % str(tgt_w))
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
        w = tgt_w[tgt_i - 1]

        # Make an entry in the dictionary with the new
        # Preterminal/Terminal combination.
        tgt_n_copy = tgt_n.copy()
        tgt_n_copy[0] = Terminal(w.value(), index=item_index(w))

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

    # TODO: Re-examine why the children in the tree are "losing" their parents.
    fix_tree_parents(tgt_t)

    # 4) Time to reattach unattached tgt words. ---
    PS_LOG.debug('#'*10+' Now reattaching unaligned words...' + '#'*10)
    aligned_indices = [t for s, t in aln]

    unaligned_tgt_words = [w for w in tgt_w if item_index(w) not in aligned_indices]


    for unaligned_tgt_word in unaligned_tgt_words:

        # Get the left and right words that are aligned...
        left_words = [w for w in tgt_w if item_index(w) < item_index(unaligned_tgt_word) and item_index(w) in aligned_indices]
        right_words= [w for w in tgt_w if item_index(w) > item_index(unaligned_tgt_word) and item_index(w) in aligned_indices]

        assert left_words or right_words, "No aligned words were found..."

        left_word = None if not left_words else left_words[-1]
        right_word= None if not right_words else right_words[0]

        # Create the new preterminal node with the label 'UNK',
        # using the ID label provided by this word, and its index
        # at the preterminal stage.
        t = IdTree('UNK', [Terminal(unaligned_tgt_word.value(), index=item_index(unaligned_tgt_word))], id=unaligned_tgt_word.id)


        # If the only aligned word found was to the right,
        # select the preterminal with a span that starts
        # at that right word's index.
        if not left_word:
            left_n = tgt_t.find_start_index(item_index(right_word))
            left_n.parent().insert_by_span(t)

        # If the only aligned word found was to the left,
        # select the preterminal with a span that ends
        # at that left word's index
        elif not right_word:
            right_n = tgt_t.find_stop_index(item_index(left_word))
            right_n.parent().insert_by_span(t)

        else:
            left_n = tgt_t.find_stop_index(item_index(left_word))
            right_n= tgt_t.find_start_index(item_index(right_word))

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

class DepEdge(object):
    """
    Container object for holding the head/child, and dependency
    type.
    """
    def __init__(self, head=None, dep=None, type=None, pos=None):
        self.head = head
        self.dep = dep
        self.type = type
        self.pos = pos

    def __eq__(self, other):
        return self.head == other.head and self.dep == other.dep and self.type == other.type and self.pos == other.pos

    def __hash__(self):
        return '{}_{}_{}_{}'.format(self.head, self.dep, self.type, self.pos)


class DepTree(IdTree):
    def __init__(self, label, children=None, id=None, type=None, word_index=None, pos=None):
        super().__init__(label, children=children, id=id)
        self.type = type
        self._word_index = word_index
        self.pos = pos

        # We must have an index for every word.
        assert isinstance(word_index, int)

    def __hash__(self):
        return hash(self._label) + hash(self.type) + hash(self.word_index) + id(self)

    def to_indices(self):
        """
        Return a representation of the deptree as just a list of
        (head, child) indices.
        """
        return [(st.parent().word_index, st.word_index) for st in self.subtrees()]

    @classmethod
    def root(cls):
        return cls('ROOT', [], type='root', word_index=0)


    @classmethod
    def fromstring(cls, tree_string, id_base='', stype=DEPSTR_STANFORD, **kwargs):
        """
        Read a dependency tree from a string using several different formats.

        ::

        :param tree_string: String to parse
        :type tree_string: str
        :param id_base: ID string on which to base the IDs in this tree.
        :type id_base: str
        :param stype: The format of the string to parse...
        """
        DS_LOG.debug('Building dependency tree from: {}'.format(tree_string))


        # =============================================================================
        # PTB-LIKE FORMAT (Bracketed, hierarchical)
        # =============================================================================

        if stype == DEPSTR_PTB:
            def parse_label(s, children):
                label, index, type = re.search('(.*?)(?:\[([0-9]+)\])(-.*?)?', s).groups()
                return cls(label, children, type=type, word_index=int(index))

            results = paren_level_contents(tree_string, f=parse_label)
            assert len(results) == 1
            return results[0]

        # =============================================================================
        # STANFORD/CONLL FORMATS (Unordered, edges)
        # =============================================================================
        else:

            edges = get_dep_edges(tree_string, stype=stype)

            dt = cls.root()

            roots = [e.head for e in edges if e.head.label == 'ROOT']

            if not roots:
                raise TreeError("No root for tree {}. Skipping.".format(tree_string))


            # Iterate through the edges, and look for those
            # that are "attachable"
            return build_dep_edges(edges)

    def pos_list(self):
        """

        :rtype : list[POSToken]
        """
        words = sorted([POSToken(st.label(), index=st.word_index, label=st.pos) for st in self.subtrees()],
                       key=lambda x: x.index)
        return words

    def to_conll(self, lowercase=False, clean_token=False, match_punc=False, multiple_heads=False, unk_pos='_'):
        """
        Return a string in CONLL format

        (see:
            http://ilk.uvt.nl/conll/

        under "Data Format")
        """

        indices = sorted(set([st.word_index for st in self.subtrees()]))

        cs = ConllSentence()
        # Add support for a node having multiple heads...
        for index in indices:

            nodes = self.findall_indices(index)
            node = nodes[0]
            head_indices = sorted(set([n.parent().word_index for n in nodes]))


            # -------------------------------------------
            # Make sure that the head is actually an index
            # that we see in the sentence.
            # -------------------------------------------
            head_indices = [i for i in head_indices if i < len(indices)]

            # -------------------------------------------
            # Really, we should have comma-separated lists of head indices
            # but, that doesn't seem to be supported in training the parser.
            # -------------------------------------------
            if not head_indices:
                head = '_'
            elif multiple_heads:
                head = ','.join([str(i) for i in head_indices])
            else:
                head = str(head_indices[0])



            # -------------------------------------------
            # Process the node label...
            # -------------------------------------------
            node_label = node.label()
            if lowercase is True:
                node_label = node_label.lower()
            if clean_token:
                node_label = clean_lang_token(node_label, lowercase=False)
            if match_punc and not node.pos:
                if re.match(punc_re_mult, node_label, flags=re.U):
                    node.pos = PUNC_TAG

            # -------------------------------------------
            # Assign the conll word stuff.
            # -------------------------------------------
            cw = ConllWord()

            cw.id = index
            cw.form = node_label
            cw.cpostag = node.pos if node.pos else unk_pos
            cw.postag  = node.pos if node.pos else unk_pos
            cw.head    = head
            cw.deprel  = node.type
            if 0 in head_indices:
                cw.deprel = 'root'
            cs.append(cw)

        return str(cs)



    @property
    def word_index(self):
        return self._word_index

    def __str__(self):
        ret_str = '(%s[%s]' % (self.label(), self.word_index)
        for child in self:
            ret_str += ' %s' % str(child)
        return ret_str + ')'

    def stanford_str(self, separator=' '):
        """
        Return a string representation in the stanford parser format.
        """
        repr = ''
        for st in self.subtrees():
            repr += '{}({}-{}, {}-{}){}'.format(st.type,
                                               st.parent().label(),
                                               st.parent().word_index,
                                               st.label(),
                                               st.word_index,
                                               separator)
        return repr

    def find_index(self, idx):
        return self.find(lambda x: x.word_index == idx)

    def findall_indices(self, idx):
        return self.findall(lambda x: x.word_index == idx)

    def find_terminal(self, term):
        assert isinstance(term, Terminal)
        return self.find(lambda t: t.word_index == term.index and t.label() == term.label)

    def find_heads(self, term):
        assert isinstance(term, Terminal)
        self.findall(lambda x: x.word_index == term.index and x.label() == term.label)

    def __eq__(self, other, check_type = True):
        if (self.word_index != other.word_index):
            return False
        elif (self.type != other.type) and check_type:
            return False
        elif len(self) != len(other):
            return False
        elif (self._label != other._label):
            return False
        for my_child, their_child in zip(self, other):
            if not my_child.__eq__(their_child, check_type):
                return False
        return True

    def structurally_eq(self, other):
        return self.__eq__(other, check_type=False)

    def similar(self, other):
        return super().similar(other) and self.word_index == other.word_index

    def span(self):
        raise TreeError('Span is not supported for dependency tree.')

    def copy(self):
        children = [c.copy() for c in self]
        dt = DepTree(copy(self.label()), children, id=copy(self.id), type=copy(self.type), word_index=copy(self.word_index))
        return dt

    def delete(self, promote=True):
        """
        By default,
        :param propagate: Whether or not to delete "empty"
         nonterminals. Default to false, since DepTrees
         don't have the same notion of nonterminal/terminal.
        """
        super().delete(propagate=False, promote=promote)

    def subtrees(self, filter=None, include_root=False):
        """
        Override the subtrees finder from the parent class
        with the default that we will not include the root.

        :param filter:
        :param include_root:
        :return: list of Deptrees
        :rtype: list[DepTree]
        """
        if not include_root:
            nonroot = lambda x: x.depth() > 0
            if filter is not None:
                return super().subtrees(filter=lambda x: filter(x) and nonroot(x))
            else:
                return super().subtrees(filter=nonroot)
        else:
            return super().subtrees(filter=filter)



def get_dep_edges(string, stype=DEPSTR_STANFORD):
    """

    :param string: A string representation of the dependency tree produced by the stanford parser.
    :return: List of DepEdges
    :rtype: list[DepEdge]
    """

    edges = []

    if stype == DEPSTR_STANFORD:
        #                    Sometimes the parser seems to place a spurious quote after the digit?
        nodes = re.findall('(\S+)\((.*?\d+)\'*\)', string)


        # We are going to store a dictionary of words
        # and their children, and then construct the
        # tree from "ROOT" on down...


        # Go through each of the returned values...
        for name, pair in nodes:
            head, child = re.split(',\s', pair)

            w_i_re = re.compile('(\S+)-(\d+)')

            head  = Terminal(*re.search(w_i_re, head).groups())
            child = Terminal(*re.search(w_i_re, child).groups())

            edge = DepEdge(head, child, type=name)
            if edge in edges:
                continue

            edges.append(edge)

    # -----------------------------------------------------------------------------
    # CONLL Dependencies...

    elif stype == DEPSTR_CONLL:
        words = string.strip().split('\n')

        # Get the indices and their associated words...
        w_d = {int(w.split()[0]):w.split()[1] for w in words}


        for word in words:
            info = word.split()

            index = int(info[0])
            form  = info[1]
            pos   = info[3]
            head  = int(info[6])
            type  = info[7]

            if head == 0:
                head_t = Terminal('ROOT', 0)
            else:
                head_t = Terminal(w_d[head], head)

            child_t = Terminal(form, index)
            edges.append(DepEdge(head_t, child_t, type=type, pos=pos))

    return edges


class Count():
    def __init__(self):
        self._i = 0

    def inc(self, n=1):
        self._i += n

    def val(self):
        return self._i

def build_dep_edges(edges):
    dt = DepTree.root()
    while edges:

        edge_found = False

        for i, edge in enumerate(edges):
            #
            node = dt.find_terminal(edge.head)

            if node is not None:
                node.append(DepTree(edge.dep.label, [], word_index=edge.dep.index, type=edge.type, pos=edge.pos))
                del edges[i]
                edge_found = True
                break

        if not edge_found:
            edge_children = [(e.dep.label,e.dep.index) for e in edges]
            raise TreeError("Dependency Tree could not be built, edges remain: {}.".format(edge_children))

    return dt

def paren_level_contents(string, f=lambda x, y: [x,y], i=None):
    """
    Tail-recursive way to parse a matched set of parens

    :param string:
    :type string: str
    :param f:
    :param init_open_parens:
    """

    # Make sure that the "i" gets re-initialized properly on
    # each call. (No mutable default args!)
    if i is None:
        i = Count()

    content = ''

    children = []

    escaped = False

    while i.val() < len(string):
        char = string[i.val()]
        i.inc() # Increment the counter...
                # this counter will persist through recursive calls

        if escaped == True:
            content += char
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == ')':
            return f(content.strip(), children)
        elif char == '(':
            children.append(paren_level_contents(string, f=f, i=i))
        else:
            content += char

    # We reach this point only after we have built up all the
    return children

def read_conll_file(path):
    """

    :rtype : list[DepTree]
    """
    f = open(path, 'r')
    string = ''
    trees = []
    for line in f:
        if not line.strip():
            if string:
                trees.append(DepTree.fromstring(string, stype=DEPSTR_CONLL))
                string = ''
        else:
            string += line

    return trees


def fix_tree_parents(t, preceding_parent = None):
    """
    For some reason, the parents are getting broken during tree projection
    reordering. So, this function will go through and reassign parents
    of nodes to reflect the top-down view.

    :param t: Input Tree
    """

    t._parent = preceding_parent

    for child in t:
        if isinstance(child, Tree):
            fix_tree_parents(child, preceding_parent=t)

# =============================================================================
# Do a CONLL export with the words from the sentence, so we don't break at training
# time if we're missing words.
# =============================================================================

def to_conll(ds, words, lowercase=False, clean_token=False, match_punc=False, multiple_heads=False, unk_pos='_'):
    """
    Return a string in CONLL format

    (see:
        http://ilk.uvt.nl/conll/

    under "Data Format")
    :type ds: DepTree
    """

    cs = ConllSentence()

    # TODO: FIXME: We really shouldn't be reattaching here, but rather in the projection
    root_word = ds.find(lambda x: x.parent() is not None and x.parent().word_index == 0)
    root_word_index = 0
    if root_word is not None:
        root_word_index = root_word.word_index

    for word in words:
        w_idx = item_index(word)
        nodes = ds.findall_indices(w_idx)
        if nodes:
            node = nodes[0]
            head_indices = sorted(set([n.parent().word_index for n in nodes]))

            # -------------------------------------------
            # Really, we should have comma-separated lists of head indices
            # but, that doesn't seem to be supported in training the parser.
            # -------------------------------------------
            if not head_indices:
                head = '_'
            elif multiple_heads:
                head = ','.join([str(i) for i in head_indices])
            else:
                head = str(head_indices[0])

            pos = node.pos
            deprel = node.type
            if 0 in head_indices:
                deprel = 'root'

        else:
            pos = None
            deprel = None
            head = root_word_index


        # -------------------------------------------
        # Process the node label...
        # -------------------------------------------
        word_form = word.value()
        if lowercase is True:
            word_form = word_form.lower()
        if clean_token:
            word_form = clean_lang_token(word_form, lowercase=False)
        if match_punc:
            if re.match(all_punc_re_mult, word_form, flags=re.U):
                pos = PUNC_TAG
                head = root_word_index


        # -------------------------------------------
        # Assign the conll word stuff.
        # -------------------------------------------
        cw = ConllWord()

        cw.id = w_idx
        cw.form = word_form
        cw.cpostag = pos if pos else unk_pos
        cw.postag  = pos if pos else unk_pos
        cw.head    = head
        cw.deprel  = deprel
        cs.append(cw)

    return str(cs)
