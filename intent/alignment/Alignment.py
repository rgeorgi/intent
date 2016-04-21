"""
Created on Feb 21, 2014

@author: rgeorgi
"""

import re, unittest, copy

class HeuristicAlignmentException(Exception): pass

#===============================================================================
# Aligned Sent Class
#===============================================================================

class AlignedSent():
    """
    An object class to contain source and target tokens, and an alignment between the two.
    """
    def __init__(self, src_tokens, tgt_tokens, aln):
        self.src_tokens = src_tokens
        self.tgt_tokens = tgt_tokens
        self.aln = aln
        self.attrs = {}

        if not isinstance(aln, Alignment):
            raise AlignmentError('Passed alignment is not of type Alignment')

        for a in self.aln:
            src_i, tgt_i = a[0],a[-1]
            if src_i - 1 >= len(self.src_tokens):
                raise AlignmentError('Source index %d is too high for %s'  % (src_i, self.src_tokens))
            if tgt_i - 1 >= len(self.tgt_tokens):
                raise AlignmentError('Target index %d is too high for sentence %s' % (tgt_i, self.tgt_tokens))

    def aln_with_nulls(self):
        """
        Return alignment with explicit NULL alignments.
        """
        new_aln = copy.copy(self.aln)
        for i, src_t in enumerate(self.src_tokens):
            if src_t.index not in [src for src, tgt in self.aln]:
                new_aln.add((src_t.index, 0))

        return new_aln


    def aligned_words(self):
        words = set([])
        for src_i, tgt_i in self.aln:
            words.add((self.src_tokens[src_i-1], self.tgt_tokens[tgt_i-1]))
        return words

    def unaligned_src_indices(self):
        for i, t in enumerate(self.src):
            if not self.pairs(src=i+1):
                yield i

    def unaligned_tgt_indices(self):
        for i, t in enumerate(self.tgt):
            if not self.pairs(tgt=i+1):
                yield i

    def unaligned_src_words(self):
        for i in self.unaligned_src_indices():
            yield self.src[i]

    def unaligned_tgt_words(self):
        for i in self.unaligned_tgt_indices():
            yield self.tgt[i]

    def flipped(self):
        return AlignedSent(self.tgt_tokens, self.src_tokens, self.aln.flip())

    def pairs(self, src=None, tgt=None):
        return [aln for aln in self.aln if (src and src==aln[0]) or (tgt and tgt==aln[1]) ]

    def wordpairs(self, ips=None):
        """
        Return the pairs of words referred to by the indices in ips.

        This is either an aribitrary pair of indices passed as an argument,
        or the indices contained in the alignment property.
        @param ips:
        """
        if ips is None:
            ips = self.aln
        return [self.wordpair(ip) for ip in ips]


    def wordpair(self, ip):
        """
        Return the wordpair corresponding with an alignment pair.
        @param ip:
        """
        return(self.src_tokens[ip[0]-1], self.tgt_tokens[ip[1]-1])

    def __str__(self):
        return '<%s, %s, %s>' % (self.src_tokens, self.tgt_tokens, self.aln)

    @property
    def src_text(self):
        return ' '.join([s.seq for s in self.src_tokens])

    @property
    def tgt_text(self):
        return ' '.join([t.seq for t in self.tgt_tokens])

    def set_attr(self, key, val):
        self.attrs[key] = val

    def get_attr(self, key):
        return self.attrs[key]

    @property
    def srclen(self):
        return len(self.src_tokens)

    @property
    def tgtlen(self):
        return len(self.tgt_tokens)

    @property
    def src(self):
        return self.src_tokens

    @property
    def tgt(self):
        return self.tgt_tokens

    def get_src(self, i):
        return self.src_tokens[i-1]

    def get_tgt(self, i):
        return self.tgt_tokens[i-1]

    def src_to_tgt(self, i):
        indices = [t for s, t in self.aln if s == i]
        if indices:
            return indices
        else:
            return [0]

    def tgt_to_src(self, i):
        indices = [s for s, t in self.aln if t == i]
        if indices:
            return indices
        else:
            return [0]

    def src_to_tgt_words(self, i):
        return [self.tgt[t-1] for s, t in self.aln if s == i and i > 0]

    def tgt_to_src_words(self, i):
        return [self.src[i-1] for s, t in self.aln if t == i and i > 0]

    def serialize_src(self):
        return ' '.join(self.serialize_src_h())

    def serialize_src_h(self):
        morphcount = 0
        for i, t in enumerate(self.src):

            # Get the tgt tokens that align with this token...
            tgt_indices = self.src_to_tgt(i+1)

            for morph in t.morphs():
                morphcount += 1

                # Align each morph to each target pair...
                for tgt_index in tgt_indices:
                    yield '%s:%s:%s' % (morphcount, i+1, tgt_index)
                    # Yield the morph_index:parent_index:tgt_index

    @classmethod
    def from_giza_lines(cls, tgt, aln):
        """
        Return the target-to-source alignment from the target and aln lines
        of giza.
        """
        # Start by getting the target tokens from the provided target line
        tgt_tokens = tokenize_string(tgt, whitespace_tokenizer)

        # next, read the alignments from the aln line.
        a = Alignment.from_giza(aln)

        # Finally, the source tokens are also on the aln line.
        alignments = re.findall('(\S+) \(\{(.*?)\}\)', aln)

        # Get the src tokens...
        src_tokens = [a[0] for a in alignments[1:]]

        # And create the aln sent.
        aln_sent = cls(src_tokens, tgt_tokens, a)
        return aln_sent




class AlignedCorpus(list):

    def __init__(self, iter=None):
        if iter is None:
            iter = []
        super().__init__(iter)

    def write(self, src_path, tgt_path, aln_path):
        src_f = open(src_path, 'w')
        tgt_f = open(tgt_path, 'w')
        aln_f = open(aln_path, 'w')

        for a_sent in self:

            src = a_sent.src_text()
            tgt = a_sent.tgt_text()
            aln = str(a_sent.aln)

            src_f.write(src+'\n')
            tgt_f.write(tgt+'\n')
            aln_f.write(aln+'\n')

        src_f.close(), tgt_f.close(), aln_f.close()

    def read(self, src_path, tgt_path, aln_path, limit=None):
        """
        Read in the morph:gloss:aln alignment format

        @param src_path: Source sents
        @param tgt_path: Target sents
        @param aln_path: Alignment filename
        @param limit: Sentence limit
        """
        src_f = open(src_path, 'r', encoding='utf-8')
        tgt_f = open(tgt_path, 'r', encoding='utf-8')
        aln_f = open(aln_path, 'r', encoding='utf-8')


        src_lines = src_f.readlines()
        tgt_lines = tgt_f.readlines()
        aln_lines = aln_f.readlines()

        src_f.close(), tgt_f.close(), aln_f.close()

        lines = zip(src_lines, tgt_lines, aln_lines)
        i = 0
        for src_line, tgt_line, aln_line in lines:
            src_tokens = src_line.split()
            tgt_tokens = tgt_line.split()

            #===================================================================
            # Read the aligment data
            #
            # The gloss-with-morph data will be read in "morph:gloss:aln" format.
            #===================================================================
            aln_tokens = aln_line.split()
            m_a = MorphAlign()

            for aln_token in aln_tokens:
                m_a.add_str(aln_token)

            a_sent = AlignedSent(src_tokens, tgt_tokens, m_a)
            self.append(a_sent)

            i+= 1
            if limit and i == limit:
                break



    def read_giza(self, src_path, tgt_path, a3, limit=None):
        """
        Method intended to read a giza A3.final file into an alignment format.

        @param src_path: path to the source sentences
        @param tgt_path: path to the target sentences
        @param a3: path to the giza A3.final file.
        @param limit:
        """
        src_f = open(src_path, 'r', encoding='utf-8')
        tgt_f = open(tgt_path, 'r', encoding='utf-8')
        aln_f = open(a3, 'r', encoding='utf-8')

        src_lines = src_f.readlines()
        tgt_lines = tgt_f.readlines()
        aln_lines = aln_f.read()

        src_f.close, tgt_f.close(), aln_f.close()

        alignments = []

        #------------------------------------------------------------------------------
        # Do all the parsing of the A3.final file.

        alns = re.findall('NULL.*', aln_lines, flags=re.M)
        for aln in alns:
            alignment = Alignment()
            elts = re.findall('\(\{([0-9\s]+)\}\)', aln)

            # Starting from 1 means we skip the NULL alignments.
            for i in range(0,len(elts)):
                elt = elts[i]
                indices = map(lambda ind: int(ind), elt.split())
                for index in indices:
                    alignment.add((i, index))
            alignments.append(alignment)

        #------------------------------------------------------------------------------
        # now, back to creating the corpus
        lines = zip(src_lines, tgt_lines, alignments)
        i = 0
        for src_line, tgt_line, aln in lines:
            a_sent = AlignedSent(src_line.split(), tgt_line.split(), aln)
            a_sent.attrs['file'] = a3
            a_sent.attrs['id'] = None
            self.append(a_sent)
            i+=1
            if limit and i == limit:
                break


#===============================================================================
# Combine AlignedSents
#===============================================================================

def union(a1, a2):
    return a1 | a2

def combine_corpora(a1, a2, method='intersect'):

    # Do some error checking
    if not isinstance(a1, AlignedCorpus) or not isinstance(a2, AlignedCorpus):
        raise AlignmentError('Attempt to intersect non-aligned corpus')
    elif len(a1) != len(a2):
        raise AlignmentError('Length of aligned corpora are mismatched')

    i_ac = AlignedCorpus()

    for a1_sent, a2_sent in zip(a1, a2):
        i_snt = combine_sents(a1_sent, a2_sent, method=method)
        i_ac.append(i_snt)
    return i_ac


def combine_sents(s1, s2, method='intersect'):
    if not isinstance(s1, AlignedSent) or not isinstance(s2, AlignedSent):
        raise AlignmentError('Attempt to intersect non-AlignedSents')
    elif s1.srclen != s2.tgtlen:
        raise AlignmentError('Length of sources do not match')
    elif s1.tgtlen != s2.srclen:
        raise AlignmentError('Length of targets do not match')

    if method == 'intersect':
        # Actually take the intersection
        return AlignedSent(s1.src_tokens, s1.tgt_tokens, s1.aln & s2.aln.flip())
    elif method == 'union':
        return AlignedSent(s1.src_tokens, s1.tgt_tokens, s1.aln | s2.aln.flip())
    elif method == 'refined':
        return refined_combine(s1, s2)
    else:
        raise AlignmentError('Unknown combining method')

def refined_combine(s1, s2):
    """

    Implements the "refined" alignment algorithm from Och & Ney 2003

    @param s1:
    @param s2:
    """
    A_1 = s1.aln
    A_2 = s2.aln.flip()

    A = A_1 & A_2

    remaining = (A_1 | A_2) - A
    while remaining:
        i, j = remaining.pop()

        # ...if neither f_j or e_i has an alignment in A..
        if not(A.contains_src(i) or A.contains_tgt(j)):
            A.add((i,j))
            continue

        # ...or if:
        #
        #  1) The alignment (i, j) has a horizontal neighbor
        #     (i-1, j), (1+1, j) or a vertical neighbor
        #     (i, j-1), (i,j+1) that is already in A
        #
        horizontal = {(i-1,j),(i+1,j)} & A
        vertical = {(i,j-1),(i,j+1)} & A

        #  2) The set A | {(i,j)} does not contain alignments
        #     with BOTH horizontal and vertical neighbors.
        if horizontal and vertical:
            continue
        else:
            A.add((i,j))


    return AlignedSent(s1.src_tokens, s1.tgt_tokens, A)






class AlignmentError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


#===============================================================================
# Alignment Class
#===============================================================================

class AlignPair(tuple):

    def __new__(cls, seq=tuple(), type=None):
        ap = super().__new__(cls, tuple(seq))
        ap.type = type
        return ap


class Alignment(set):
    """
    Simply, a set of (src_index, tgt_index) pairs in a set.
    """

    def __init__(self, iter=list(), type=None):
        super().__init__(iter)
        self.type = type

    def add(self, *args, **kwargs):
        for arg in args[0]:
            assert isinstance(arg, int), type(arg)
        super().add(*args, **kwargs)

    def __str__(self):
        return 'Alignment{'+', '.join([str(e) for e in sorted(self)])+'}'

    def contains_tgt(self, key):
        return bool([tgt for src,tgt in self if tgt==key])

    @classmethod
    def from_giza(cls, giza):
        """
        | Given a giza style alignment string, such as:
        |
        | ``NULL ({ 3 }) fact ({ }) 1ss ({ 1 }) refl ({ }) wash ({ 2 }) ben ({ 5 4 }) punc ({ }) ne ({ 6 }) shirt ({ 4 })``
        |
        ...where the integers represent an indexed-from-one reference to the target line, and the
        words are tokens from the source line, return a (src, tgt) index alignment.


        :param giza: Alignment string as described above.
        :type giza: str
        """
        # Initialize the alignment.
        a = cls()

        patterns = re.findall('\S+\s\(\{(.*?)\}\)', giza)

        # Skip the first (null) alignment, and iterate over
        # the remaining indices
        for i, index_str in enumerate(patterns[1:], start=1):
            tgt_indices = [int(i) for i in index_str.split()]
            for tgt_index in tgt_indices:
                a.add((i, tgt_index))

        # Return the alignment.
        return a

    # -------------------------------------------
    # UNION AND INTERSECTION
    # -------------------------------------------
    # Just here for the purposes of type-hinting.

    def intersection(self, *args, **kwargs):
        """
        :rtype: Alignment
        """
        return Alignment(super().intersection(*args, **kwargs))

    def union(self, *args, **kwargs):
        """
        :rtype: Alignment
        """
        return Alignment(super().union(self, *args, **kwargs))

    def copy(self, *args, **kwargs):
        """
        :rtype: Alignment
        """
        return Alignment(super().copy(*args, **kwargs))
    # -------------------------------------------

    def grow_diag(self, a2):

        # -------------------------------------------
        # 1) Start by getting the intersection and union
        """
        :rtype: Alignment
        """
        intersection = self.intersection(a2)
        union        = self.union(a2)

        new_alignment = intersection.copy()

        # -------------------------------------------
        # 2) Now, for each aligned point, see if one of the
        #    e or f portions are in the intersection, and the

        neighboring = ((-1,0),(0,-1),(1,0),(0,1),(-1,-1),(-1,1),(1,-1),(1,1))

        e_indices = set([e for e, f in intersection])
        f_indices = set([f for e, f in intersection])

        for e, f in intersection:
            for e_offset, f_offset in neighboring:
                e_new = e + e_offset
                f_new = f + f_offset

                if ((not intersection.contains_src(e_new) or
                     not intersection.contains_tgt(f_new)) and
                    (e_new, f_new) in union):

                    new_alignment.add((e_new, f_new))

        return new_alignment

    def grow_diag_final(self, a2):
        new_alignment = self.grow_diag(a2)
        new_alignment = new_alignment.final(self)
        new_alignment = new_alignment.final(a2)
        return new_alignment

    def final(self, a):
        """
        :rtype: Alignment
        """
        new_alignment = self.copy()
        # -------------------------------------------
        # 1) for the alignments in the provided alignment...
        #    if one of the points is unaligned in ourselves,
        #    add it.
        for e, f in a:
            if (not self.contains_src(e) or not self.contains_tgt(f)):
                new_alignment.add((e,f))

        return new_alignment



    def flip(self):
        """
        For an alignment of ``{ (a, b) ... (c, d) }`` pairs, return an :py:class:`Alignment` of
        ``{ (b, a) ... (d, c) }``

        :rtype: Alignment
        """
        return Alignment([(y, x) for x, y in self])

    def contains_src(self, key):
        return bool([src for src,tgt in self if src==key])

    def __sub__(self, o):
        return self.__class__(set.__sub__(self, o))

    def nonzeros(self):
        nz = [elt for elt in self if elt[0] > 0 and elt[-1] > 0]
        return self.__class__(nz)

    def serialize_src(self):
        return ' '.join([':'.join([str(b) for b in a]) for a in self])

    def src_to_tgt(self, key):
        return [tgt for src, tgt in self if src == key]

    def tgt_to_src(self, key):
        return [src for src, tgt in self if tgt == key]

    def all_src(self):
        return set([src for src, tgt in self])

    def all_tgt(self):
        return set([tgt for src, tgt in self])


#===============================================================================
# MorphAlign Class
#===============================================================================
class MorphAlign(Alignment):
    """
    Special subclass of alignment that holds not only src and tgt indices, but also
    a remapped middle index
    """
    def __init__(self, iter=[]):
        self._remapping = {}
        Alignment.__init__(self, iter)

    def add(self, item):
        Alignment.add(self, item)
        self._remapping[item[0]] = item[1]

    def flip(self):
        return MorphAlign([(c,b,a) for a,b,c in self])

    def add_str(self, string):
        src,parent,tgts = string.split(':')
        for tgt in tgts.split(','):
            self.add((int(src),int(parent),int(tgt)))

    @property
    def GlossAlign(self):
        return Alignment((aln[1],aln[-1]) for aln in self)

    @property
    def MorphAlign(self):
        return Alignment((aln[0], aln[-1]) for aln in self)

    def remap(self, aln):
        """
        Given another alignment, return a new alignment where its indices are either
        either remapped to an entry in the remapping, or returned as-is.

        @param aln: Alignment to remap.
        """
        return Alignment((self.remapping.get(elt[0], elt[0]), elt[-1]) for elt in aln)

    @property
    def remapping(self):
        return self._remapping

# =============================================================================
# General-Purpose Method for heuristic alignment
#
#  Use this function to do the back-and-forth iteration with varying
# comparison functions.
# =============================================================================

def exact_match(src, tgt):
    return str(src) == str(tgt)

def stem_match(src, tgt):
    return lemmatize_token(str(src)) == lemmatize_token(str(tgt))

def gram_match(src, tgt):
    return str(tgt).lower() in gramdict.get(str(src).lower(), [])

def heuristic_chain(gloss_tokens, trans_tokens, methods, aln = None, multiple_matches = True):

    if aln is None:
        aln = Alignment()

    for method in methods:
        aln = heuristic_iteration(gloss_tokens, trans_tokens, aln, method, multiple_matches = multiple_matches)
    return aln

def heuristic_iteration(gloss_tokens, trans_tokens, aln, comparison_function, multiple_matches = True, iteration=1, report=False):
    """

    :param gloss_tokens:
    :type gloss_tokens: list[str]
    :param trans_tokens:
    :type trans_tokens: list[str]
    :param aln:
    :type aln: Alignment
    :param comparison_function:
    :param iteration:
    """

    gloss_indices = range(0, len(gloss_tokens))
    trans_indices = range(0, len(trans_tokens))

    # On the second pass, let's move from the right
    # backward
    if iteration > 1:
        gloss_indices = gloss_indices[::-1]
        trans_indices = trans_indices[::-1]

    aligned_gloss_w = set(aln.all_src())
    aligned_trans_w = set(aln.all_tgt())

    for gloss_i in gloss_indices:

        # Only allow one alignment from gloss to trans.
        if gloss_i+1 in aligned_gloss_w:
            continue

        gloss_w = gloss_tokens[gloss_i]
        for trans_i in trans_indices:
            trans_w = trans_tokens[trans_i]

            # Skip any attempt to align already aligned words on the first pass.
            if iteration == 1 and trans_i+1 in aligned_trans_w:
                continue

            if comparison_function(gloss_w, trans_w):
                if report:
                    print('ADDING "{}"--"{}"'.format(gloss_w, trans_w))
                aln.add((gloss_i+1, trans_i+1))
                aligned_gloss_w.add(gloss_i+1)
                aligned_trans_w.add(trans_i+1)
                if iteration == 1: break # On the first iteration, let's move to another




    if iteration == 2 or not multiple_matches:
        return aln
    else:
        return heuristic_iteration(gloss_tokens, trans_tokens, aln, comparison_function, multiple_matches, iteration+1)



def heur_alignments(gloss_tokens, trans_tokens, **kwargs):
    """
    Obtain heuristic alignments between gloss and translation tokens

    :param gloss_tokens: The gloss tokens
    :type gloss_tokens: list[Token]
    :param trans_tokens: The trans tokens
    :type trans_tokens: list[Token]
    :param iteration: Number of iterations looking for matches
    :type iteration: int
    """
    if kwargs.get('lowercase', True):
        gloss_tokens = [str(g).lower() for g in gloss_tokens]
        trans_tokens = [str(t).lower() for t in trans_tokens]

    methods = [exact_match]
    if kwargs.get('stem', True):
        methods.append(stem_match)

    if kwargs.get('grams', True):
        methods.append(gram_match)

    aln = heuristic_chain(gloss_tokens, trans_tokens, methods, multiple_matches=kwargs.get('no_multiples'))

    gp = kwargs.get('gloss_pos')
    tp = kwargs.get('trans_pos')

    if gp is not None and tp is not None:
        old_aln = aln.copy()
        gp = [g.value() for g in gp]
        tp = [t.value() for t in tp]
        aln = heuristic_iteration(gp, tp, aln, exact_match, multiple_matches=False, report=False)

        # print('{} new alignments added to {} old alignments'.format(len(aln - old_aln), len(old_aln)))

    return aln

# =============================================================================
# Symmetricization Heuristics
# =============================================================================
def intersect(a1, a2):
    pass

def union(a1, a2):
    pass

#===============================================================================
# Unit tests
#===============================================================================

class AlignedSentOutputCase(unittest.TestCase):
    def runTest(self):
        s1 = tokenize_string('This is a test sentence')
        s2 = tokenize_string('test sentence this is')
        a = Alignment([(1,3),(2,4),(4,1),(5,2)])

        a_sent = AlignedSent(s1, s2, a)



class AlignmentTest(unittest.TestCase):
    def runTest(self):
        a1 = Alignment([(1,3),(2,4),(4,1),(5,2)])
        a2 = Alignment([(5,2),(4,1),(2,4),(1,3)])
        a3 = Alignment([(4,2),(3,1),(2,4),(1,3),(5,1)])

        self.assertEqual(a1,a2)
        self.assertTrue(a1.contains_src(1))
        self.assertNotEqual(a1, a3)
        self.assertNotEqual(a2,a3)
        self.assertTrue(a1.contains_src(5))
        self.assertTrue(a1.contains_tgt(3))
        self.assertFalse(a1.contains_tgt(5))
        self.assertFalse(a1.contains_src(3))

class GizaAlignmentTest(unittest.TestCase):

    def setUp(self):
        self.aln = 'NULL ({ 3 }) fact ({ }) 1ss ({ 1 }) refl ({ }) wash ({ 2 }) ben ({ 5 4 }) punc ({ }) ne ({ 6 }) shirt ({ 4 })'
        self.tgt = 'i washed the shirt for myself'

        self.a2 = Alignment([(2,1),(4,2),(5,5),(5,4), (7,6),(8,4)])

    def test_alignment_reading(self):
        a1 = Alignment.from_giza(self.aln)
        self.assertEquals(a1, self.a2)

    def test_alignmentsent_reading(self):

        a_snt = AlignedSent.from_giza_lines(self.tgt, self.aln)
        self.assertEquals(a_snt.aln, self.a2)

from intent.igt.grams import gramdict
from intent.utils.string_utils import lemmatize_token
from intent.utils.token import tokenize_string, whitespace_tokenizer, Token