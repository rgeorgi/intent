# coding=UTF-8
"""
Subclassing of the xigt package to add a few convenience methods.
"""

#===============================================================================
# Logging
#===============================================================================

import copy
import logging
import re
import string

from intent.consts import *
from intent.interfaces.fast_align import fast_align_sents
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.pos.TagMap import TagMap
from intent.utils.string_utils import replace_invalid_xml
from xigt import ref
from xigt.consts import ALIGNMENT, SEGMENTATION, CONTENT
from xigt.errors import XigtError
from xigt.metadata import Metadata, Meta
from xigt.model import XigtCorpus, Igt, Item, Tier
from .exceptions import *
from .metadata import set_meta_attr, find_meta_attr, del_meta_attr, set_intent_method, get_intent_method, \
    set_intent_proj_data

# Set up logging ---------------------------------------------------------------
from xigt.ref import ids

PARSELOG = logging.getLogger(__name__)
ALIGN_LOG = logging.getLogger('GIZA_LN')
ODIN_LOG = logging.getLogger('ODIN_LOOKUP')
CONVERT_LOG = logging.getLogger('CONVERSION')

# XIGT imports -----------------------------------------------------------------
from xigt.codecs import xigtxml

# INTERNAL imports -------------------------------------------------------------


import intent.utils.token
from intent.utils.env import c, classifier
from intent.alignment.Alignment import Alignment, heur_alignments, AlignmentError
from intent.utils.token import Token, POSToken, sentence_tokenizer, whitespace_tokenizer
from intent.interfaces.giza import GizaAligner

# Other imports ----------------------------------------------------------------
from collections import defaultdict

#===============================================================================
# Mixins
#===============================================================================

class FindMixin():
    """
    Extension of the recursive search for non-iterable elements.
    """

    # FindMixin objects should have an index.
    index = None

    def find(self, **kwargs):
        return find_in_obj(self, **kwargs)

    def findall(self, **kwargs):
        return findall_in_obj(self, **kwargs)

class RecursiveFindMixin(FindMixin):

    # Define the FindMixin as iterable,
    # but don't implement the class.
    def __iter__(self): pass



#===============================================================================
# • Parse Tree Functions ---
#===============================================================================
def read_pt(tier):

    # Assume that we are reading from a phrase structure tier.
    assert tier.type == PS_TIER_TYPE

    # Provide a way to look up the nodes by their ID so we can
    # pair them directly later...
    node_dict = {}

    # Also, keep track of the child-parent relationships that need
    # to be constructed.
    children_dict = defaultdict(list)

    for node in tier:

        # 1) If the node has an alignment, that means it's a terminal ----------
        aln = node.attributes.get(ALIGNMENT)
        if aln:
            word_item = find_in_obj(tier.igt, id=aln)
            n = IdTree(node.value(), [Terminal(word_item.value(), item_index(word_item))])

            # If this is a preterminal, it shouldn't have children.
            assert not node.attributes.get(PS_CHILD_ATTRIBUTE)


        else:
            n = IdTree(node.value(), [])

            # 2) If there is a "children" attribute, split it on whitespace and store ---
            #    those IDs to revisit, with the current node as the parent.
            childids = node.attributes.get(PS_CHILD_ATTRIBUTE, '').split()

            for childid in childids:
                children_dict[node.id].append(childid)


        node_dict[node.id] = n


    # 3) Revisit the children and make the linkages.
    child_n = None
    for parent_id in children_dict.keys():
        parent_n = node_dict[parent_id]
        for child_id in children_dict[parent_id]:
            child_n = node_dict[child_id]
            parent_n.append(child_n)


    # Finally, pick an arbitrary node, and try to find the root.
    assert child_n, "There should have been at least one child found..."

    return child_n.root()


def read_ds(tier, pos_source=None):
    """
    Like read_pt above, given a DS tier, return the DepTree object

    :param tier:
    :type tier: RGTier
    """

    # First, assert that the type we're looking at is correct.
    assert tier.type == DS_TIER_TYPE

    # --1) Root the tree.
    root = DepTree.root()

    # --2) We will build up a list of edges, then attach the edges to the tree.
    edges = []

    # --2b) Retrieve the POS tier, if it exists, in advance.
    pos_tier = get_pos_tags(tier.igt, tier.attributes.get(DS_DEP_ATTRIBUTE), tag_method=pos_source)

    for item in tier:
        dep  = item.attributes.get(DS_DEP_ATTRIBUTE)
        head = item.attributes.get(DS_HEAD_ATTRIBUTE)

        # Get the POS tag if it exists
        pos = None
        if pos_tier:
            pos_item = find_in_obj(pos_tier, alignment=dep)
            if pos_item:
                pos = pos_item.value()

        # Get the word value...
        dep_w = find_in_obj(tier.igt, id=dep)
        dep_t = Terminal(dep_w.value(), item_index(dep_w))

        if head is not None:
            head_w = find_in_obj(tier.igt, id=head)
            head_t = Terminal(head_w.value(), item_index(head_w))
        else:
            head_t = Terminal('ROOT', 0)

        e = DepEdge(head=head_t, dep=dep_t, type=item.value(), pos=pos)
        edges.append(e)

    dt = build_dep_edges(edges)
    return dt


def gen_tier_id(inst, id_base, tier_type=None, alignment=None, no_hyphenate=False):
    """
    Unified method to generate a tier ID string. (See: https://github.com/goodmami/xigt/wiki/Conventions)
    """

    # In order to number this item correctly, we need to decide how many tiers of the same type
    # there are. This is done by systematically adding filters to the list.
    filters = []

    # First, do we align with another item? (Either segmentation, alignment, or head/dep)
    if alignment is not None:
        filters.append(lambda x: aln_match(alignment)(x) or seg_match(alignment)(x) or ref_match(x, alignment, DS_HEAD_ATTRIBUTE))

    # Next, does the type match ours?
    if tier_type is not None:
        filters.append(type_match(tier_type))

    # Get the number of tiers that match this.
    if not filters:
        num_tiers = 0
    else:
        prev_tiers = findall_in_obj(inst, others=filters)
        num_tiers = len(prev_tiers)


    id_str = id_base
    # Now, if we have specified the alignment, we also want to prepend
    # that to the generated id string.
    if alignment is not None:
        if no_hyphenate:
            return '{}{}'.format(alignment, id_str)
        else:
            id_str = '{}-{}'.format(alignment, id_str)

    # Finally, if we have multiple tiers of the same type that annotate the
    # same item, we should append a letter for the different analyses.
    if num_tiers > 0 and find_in_obj(inst, id=id_str) is not None:
        while True:
            letters = string.ascii_lowercase
            assert num_tiers < 26, "More than 26 alternative analyses not currently supported"
            potential_id = id_str + '_{}'.format(letters[num_tiers])

            if find_in_obj(inst, id=potential_id) is None:
                id_str = potential_id
                break
            else:
                num_tiers += 1

    return id_str


# ===============================================================================


class RGCorpus(XigtCorpus, RecursiveFindMixin):

    def askIgtId(self):
        return gen_item_id('i', len(self.igts))

    def copy(self, limit=None):
        """
        :rtype: RGCorpus
        """
        new_c = RGCorpus(id=self.id, attributes=copy.deepcopy(self.attributes), metadata=copy.copy(self.metadata), igts=None)

        for i, igt in enumerate(self.igts):
            new_c.append(igt.copy(parent=new_c))

            if limit and i >= limit:
                break

        return new_c

    @classmethod
    def from_raw_txt(cls, txt):
        """

        :rtype: RGCorpus
        """
        print("Creating XIGT corpus from raw text...")
        xc = cls()

        PARSELOG.debug("Replacing invalid XML...")
        data = replace_invalid_xml(txt)

        instances = []
        cur_lines = []

        for line in data.split('\n'):

            if not line.strip():

                instances.append('\n'.join(cur_lines))
                cur_lines = []
                continue
            else:
                cur_lines.append(line)

        if cur_lines:
            instances.append('\n'.join(cur_lines))

        for instance in instances:
            i = RGIgt.fromRawText(instance, corpus=xc)
            xc.append(i)


        print("{} instances parsed.".format(len(xc)))
        return xc

    @classmethod
    def from_txt(cls, text, require_trans = True, require_gloss = True, require_lang = True, limit = None):
        """
        Read in a odin-style textfile to create the xigt corpus.

        """
        # Initialize the corpus
        xc = cls()

        # Replace invalid characters...
        data = replace_invalid_xml(text)

        # Read all the text lines
        inst_txts = re.findall('doc_id=[\s\S]+?\n\n', data)

        #=======================================================================
        # Begin parsing...
        #=======================================================================

        parsed = 0
        PARSELOG.info('Beginning parse')
        for inst_num, inst_txt in enumerate(inst_txts):

            if parsed % 250 == 0:
                PARSELOG.info('Parsing instance %d...' % parsed)
                pass

            # Handle the requirement for 1_to_1 alignment.
            try:
                i = RGIgt.fromString(inst_txt, corpus=xc, idnum=inst_num)
            except GlossLangAlignException as glae:
                PARSELOG.warn('Gloss and language could not be automatically aligned for instance "%s". Skipping' % gen_item_id('i', inst_num))
                continue

            # Try to get the translation line. ---------------------------------
            try:
                hastrans = trans_line(i)
            except NoTransLineException as ntle:
                PARSELOG.info(ntle)
                hastrans = False

            # Try to get the gloss line. --------------------------------------
            try:
                hasgloss = i.gloss
            except NoGlossLineException as ngle:
                PARSELOG.info(ngle)
                hasgloss = False

            # Try to get the language line. ------------------------------------
            try:
                haslang = i.lang
            except NoLangLineException as nlle:
                PARSELOG.info(nlle)
                haslang = False


            parsed +=1


            trans_constraint = (hastrans and require_trans) or (not require_trans)
            gloss_constraint = (hasgloss and require_gloss) or (not require_gloss)
            lang_constraint  = (haslang  and require_lang)  or (not require_lang)

            if trans_constraint and gloss_constraint and lang_constraint:
                xc.append(i)
            else:
                PARSELOG.info('Requirements for instance "%s" were not satisfied. Skipping' % i.id)

            # If we have reached the limit of instances that have been requested,
            # stop processing.
            if limit is not None and limit == parsed: break



        # Return the corpus
        return xc

    @classmethod
    def loads(cls, s):
        xc = xigtxml.loads(s)
        xc.__class__ = RGCorpus
        xc._finish_load()
        return xc

    def __getitem__(self, item):
        """

        :rtype : RGIgt
        """
        return super().__getitem__(item)

    def __iter__(self):
        """

        :rtype : RGIgt
        """
        return super().__iter__()

    @classmethod
    def loads(cls, s, basic_processing=False):
        """
        :rtype: RGCorpus
        """
        xc = xigtxml.loads(s)
        xc.__class__ = RGCorpus
        xc._finish_load(basic_processing)

        return xc

    @classmethod
    def load(cls, path, basic_processing = False, mode='full'):
        """
        :rtype : RGCorpus
        """
        xc = xigtxml.load(path, mode=mode)
        xc.__class__ = RGCorpus
        xc._finish_load(basic_processing)




        return xc

    def _finish_load(self, basic_processing=False):
        # Now, convert all the IGT instances to RGIgt instances.
        for igt in self.igts:
            igt.__class__ = RGIgt

            for tier in igt.tiers:
                tier.__class__ = RGTier

                for i, item in enumerate(tier):
                    item.__class__ = RGItem
                    item.index = i+1

       # If asked, we will also do some
        # basic-level enrichment...
        if basic_processing:
            for inst in self:
                try:
                    inst.basic_processing()
                except XigtFormatException as xfe:
                    PARSELOG.warn("Basic processing failed for instance {}".format(inst.id))
                except GlossLangAlignException as gae:
                    PARSELOG.warn("Gloss and language did not align for instance {}.".format(inst.id))


    def filter(self, func):
        new_igts = []
        for i in self:
            try:
                val = func(i)
            except Exception:
                pass
            else:
                if val not in [None, False]:
                    new_igts.append(i)

        self.igts = new_igts

    def attr_filter(self, attr):
        new_igts = []
        for i in self:
            try:
                tier = getattr(i, attr)
            except XigtFormatException as tpe:
                PARSELOG.info(tpe)
            else:
                new_igts.append(i)

        self.igts = new_igts

    def require_trans_lines(self):
        self.attr_filter('trans')

    def require_gloss_lines(self):
        self.attr_filter('gloss')

    def require_lang_lines(self):
        self.attr_filter('lang')

    def require_one_to_one(self):
        self.require_gloss_lines()
        self.require_lang_lines()
        new_igts = []
        for i in self:
            if len(i.gloss) == len(i.lang):
                new_igts.append(i)
            else:
                PARSELOG.info('Filtered out "%s" because gloss and lang not same length.')
        self.igts = new_igts

    def require_gloss_pos(self):
        self.filter(lambda inst: inst.get_pos_tags(GLOSS_WORD_ID) is not None)

    def remove_alignments(self, aln_method=None):
        """
        Remove alignment information from all instances.
        """
        filters = []
        if aln_method is not None:
            filters = [lambda x: get_intent_method(x) == aln_method]

        for inst in self:
            for t in inst.findall(type=ALN_TIER_TYPE, others=filters):
                t.delete()



    def giza_align_t_g(self, aligner=ALIGNER_GIZA, resume = True, use_heur = False, symmetric = SYMMETRIC_INTERSECT):
        """
        Perform giza alignments on the gloss and translation
        lines.

        :param resume: Whether to "resume" from the saved aligner, or start fresh.
        :type resume: bool
        """

        # -------------------------------------------
        # Start a list of the sentences and the associated
        # instance IDs, so we will know after alignment
        # which alignments go with which sentence.
        # -------------------------------------------
        g_sents = []
        t_sents = []

        # Keep track of which igt IDs are associated
        # with which indices of the aligner output.
        id_pairs = {}

        g_morphs = []
        t_words = []

        i = 0

        for inst in self:
            g_sent = []
            t_sent = []

            try:
                gloss_tokens, trans_tokens = tier_tokens(glosses(inst)), tier_tokens(trans(inst))

                # -------------------------------------------
                # Only add the sentences if
                if gloss_tokens and trans_tokens:

                    for gloss_token in gloss_tokens:
                        g_sent.append(re.sub('\s+','', gloss_token.value().lower()))
                    g_sents.append(g_sent)

                    for trans_token in trans_tokens:
                        t_sent.append(re.sub('\s+', '', trans_token.value().lower()))
                    t_sents.append(t_sent)

                    # -------------------------------------------
                    # If we ask for the augmented alignment...
                    # -------------------------------------------
                    if use_heur:
                        try:
                            # Try obtaining the tw/gm alignment.
                            pairs = get_trans_gloss_wordpairs(inst, aln_method=[INTENT_ALN_HEUR, INTENT_ALN_HEURPOS], all_morphs=True)
                        except ProjectionTransGlossException as ptge:
                            ALIGN_LOG.warn("Augmented giza was requested but no heur alignment is present.")
                        else:
                            # For each trans_word/gloss_word index...
                            for t_w, g_m in pairs:
                                t_words.append([t_w.lower()])
                                g_morphs.append([g_m.lower()])

                    id_pairs[inst.id] = i
                    i+=1

            except (NoNormLineException, MultipleNormLineException) as nnle:
                continue


        # Tack on the heuristically aligned g/t words
        # to the end of the sents, so they won't mess
        # up alignment.

        g_sents.extend(g_morphs)
        t_sents.extend(t_words)


        if aligner == ALIGNER_FASTALIGN:
            PARSELOG.info('Attempting to align corpus "{}" using fastalign'.format(self.id))
            g_t_alignments = fast_align_sents(g_sents, t_sents)
            t_g_alignments = fast_align_sents(t_sents, g_sents)

        elif aligner == ALIGNER_GIZA:
            PARSELOG.info('Attempting to align corpus "{}" with giza'.format(self.id))

            if resume:
                ALIGN_LOG.info('Using pre-saved giza alignment.')
                # Next, load up the saved gloss-trans giza alignment model
                ga = GizaAligner.load(c.getpath('g_t_dir'))

                # ...and use it to align the gloss line to the translation line.
                g_t_alignments = ga.force_align(g_sents, t_sents)

                # If we are applying a symmetricization heuristic AND we are
                # forcing alignment, load the reverse model.
                if symmetric is not None:
                    ga_reverse = GizaAligner.load(c.getpath('g_t_reverse_dir'))
                    t_g_alignments = ga_reverse.force_align(t_sents, g_sents)


            # Otherwise, start a fresh alignment model.
            else:
                ga = GizaAligner()
                g_t_alignments = ga.temp_train(g_sents, t_sents)

                if symmetric:
                    t_g_alignments = ga.temp_train(t_sents, g_sents)


        # -------------------------------------------
        # Apply the symmetricization heuristic to
        # the alignments if one is specified.
        # -------------------------------------------
        if symmetric:
            for i, pairs in enumerate(zip(g_t_alignments, t_g_alignments)):
                g_t, t_g = pairs
                if not hasattr(g_t, symmetric):
                    raise AlignmentError('Unimplemented symmetricization heuristic "{}"'.format(symmetric))

                g_t_alignments[i] = getattr(g_t, symmetric)(t_g.flip())

        # -------------------------------------------
        # Check to make sure the correct number of alignments
        # is returned
        # -------------------------------------------
        if len(g_t_alignments) != i:
            raise AlignmentError('Something went wrong with statistical alignment, {} alignments were returned, {} expected.'.format(len(g_t_alignments), i))

        # -------------------------------------------
        # Next, iterate through the aligned sentences and assign their alignments
        # to the instance.
        # -------------------------------------------
        if use_heur:
            aln_method = INTENT_ALN_GIZAHEUR
        else:
            aln_method = INTENT_ALN_GIZA

        for igt in self:
            if igt.id in id_pairs:
                g_t_asent = g_t_alignments[id_pairs[igt.id]]
                t_g_aln = g_t_asent.flip()
                set_bilingual_alignment(igt, igt.trans, igt.glosses, t_g_aln, aln_method = aln_method)


    def giza_align_l_t(self, symmetric = None):
        """
        Perform giza alignments directly from language to translation lines, for comparison

        :rtype: Alignment
        """

        l_sents = [i.lang.text(return_list=True) for i in self]
        t_sents = [i.trans.text(return_list=True) for i in self]

        ga = GizaAligner()

        t_l_sents = ga.temp_train(t_sents, l_sents)

        assert len(t_l_sents) == len(self)

        if symmetric is not None:
            l_t_sents = ga.temp_train(l_sents, t_sents)


        for i, igt in enumerate(self):
            t_l = t_l_sents[i]

            # If we want these symmetricized...
            if symmetric is not None:

                # Get the l_t (the "reverse" alignment)
                l_t = l_t_sents[i]

                # Ensure that the requested symmetricization heuristic is implemented...
                if not hasattr(t_l, symmetric):
                    raise AlignmentError('Unimplemented symmetricization heuristic "{}"'.format(symmetric))

                # Now, apply it (and make sure to flip the reversed alignment)
                t_l = getattr(t_l, symmetric)(l_t.flip())

            # Finally, set the resulting trans-to-lang alignment in the instance
            set_bilingual_alignment(igt, igt.trans, igt.lang, t_l, aln_method = INTENT_ALN_GIZA)



    def heur_align(self, error=False, use_pos=False, **kwargs):
        """
        Perform heuristic alignment between the gloss and translation.
        """
        for igt in self:
            try:
                PARSELOG.info('Attempting to heuristically align instance "{}"'.format(igt.id))
                g_heur_aln = igt.heur_align(use_pos=use_pos, **kwargs)
            except NoTransLineException as ntle:
                PARSELOG.warning(ntle)
                if error:
                    raise ntle
            except (NoGlossLineException, NoTransLineException, NoLangLineException, EmptyGlossException) as ngle:
                PARSELOG.warning(ngle)
                if error:
                    raise ngle
            except MultipleNormLineException as mnle:
                PARSELOG.warning(mnle)
                if error:
                    raise mnle
            except XigtError as xe:
                PARSELOG.critical('XigtError in "{}"'.format(igt.id))
                raise xe




#===============================================================================
# IGT Class
#===============================================================================



class RGIgt(Igt, RecursiveFindMixin):

    # • Constructors -----------------------------------------------------------

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Add a default bit of metadata...
        self.metadata = [RGMetadata(type='xigt-meta',
                                text=[RGMeta(type='language',
                                             attributes={'name':'english',
                                                        'iso-639-3':'eng',
                                                        'tiers':'glosses translations'}
                                            )])]

        #self.metadata = mdt

    def all_tags(self):
        tag_list = []
        for item in self.raw_tier():
            item_tags = re.split('[\+\-]', item.attributes['tag'])
            tag_list.extend(item_tags)
        return tag_list


    def has_corruption(self):
        """
        Return True if instance has "CR" in it, indicating corruption.
        """
        return 'CR' in self.all_tags()

    def has_double_column(self):
        return 'DB' in self.all_tags()

    @classmethod
    def fromRawText(cls, string, corpus = None, idnum=None):
        return from_raw_text(string, corpus, idnum)


    @classmethod
    def fromString(cls, string, corpus = None, idnum=None):
        """
        Method to parse and create an IGT instance from odin-style text.
        """

        # Start by looking for the doc_id, and the line range.
        doc_re = re.search('doc_id=(\S+)\s([0-9]+)\s([0-9]+)\s(.*)\n', string)
        docid, lnstart, lnstop, tagtypes = doc_re.groups()

        if idnum is not None:
            id = gen_item_id('i', idnum)
        elif corpus:
            id = corpus.askIgtId()
        else:
            corpus = RGCorpus()
            id = corpus.askIgtId()

        inst = cls(id = id, attributes={'doc-id':docid,
                                            'line-range':'%s %s' % (lnstart, lnstop),
                                            'tag-types':tagtypes})

        # Now, find all the lines
        lines = re.findall('line=([0-9]+)\stag=(\S+):(.*)\n?', string)

        # --- 3) Create a raw tier.
        rt = RGLineTier(id = RAW_ID, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE}, igt=inst)

        for lineno, linetag, linetxt in lines:
            l = RGLine(id = rt.askItemId(), text=linetxt, attributes={'tag':linetag, 'line':lineno}, tier=rt)
            rt.append(l)

        inst.append(rt)

        # --- 4) Do the enriching if necessary

        inst.basic_processing()

        return inst

    def copy(self, parent = None):
        """
        Perform a custom deepcopy of ourselves.
        :rtype: RGIgt
        """
        new_i = RGIgt(id = self.id, type=self.type,
                    attributes = copy.deepcopy(self.attributes),
                    metadata = copy.copy(self.metadata),
                    corpus=parent)

        for tier in self.tiers:
            new_i.append(tier.copy(parent=new_i))

        return new_i



    # • Processing of newly created instances ----------------------------------

    def basic_processing(self):
        # Create the clean tier
        """
        Finish the loading actions of an IGT instance. (Create the normal and
        clean tiers if they don't exist...)

        """
        self.clean_tier()
        self.normal_tier()

        # Create the word and phrase tiers...
        try:
            self.trans
        except XigtFormatException:
            pass

        try:
            self.gloss
        except XigtFormatException:
            pass

        try:
            haslang = self.lang
        except XigtFormatException:
            haslang = False

        # Create the morpheme tiers...
        try:
            hasgloss = self.glosses
        except NoGlossLineException:
            hasgloss = False

        try:
            self.morphemes
        except NoLangLineException:
            pass

        # And do word-to-word alignment if it's not already done.
        if hasgloss and haslang and not self.gloss.alignment:
            word_align(self.gloss, self.lang)

        if hasgloss and haslang:
            self.add_gloss_lang_alignments()


    def add_gloss_lang_alignments(self):
        # Finally, do morpheme-to-morpheme alignment between gloss
        # and language if it's not already done...
        if not self.glosses.alignment:
            morph_align(self.glosses, self.morphemes)

        if not self.gloss.alignment:
            word_align(self.gloss, self.lang)

    # • Basic Tier Creation ------------------------------------------------------------

    def raw_tier(self):
        return get_raw_tier(self)

    def clean_tier(self, merge=False, generate=True):
        return get_clean_tier(self, merge, generate)


    def add_raw_tier(self, lines):
        add_text_tier_from_lines(self, lines, RAW_ID, RAW_STATE)

    def add_clean_tier(self, lines):
        add_text_tier_from_lines(self, lines, CLEAN_ID, CLEAN_STATE)

    def add_normal_tier(self, lines):
        add_text_tier_from_lines(self, lines, NORM_ID, NORM_STATE)


    # • Word Tier Creation -----------------------------------

    def add_normal_line(self, tier, tag, func):
        add_normal_line_to_tier(self, tier, tag, func)

    def normal_tier(self, clean=True, generate=True):
        return get_normal_tier(self, clean, generate)

    # • Words Tiers ------------------------------------------------------------

    @property
    def lang(self):
        try:
            lt = retrieve_lang_words(self)
        except NoNormLineException:
            raise NoLangLineException('No lang line available for igt "%s"' % self.id)
        else:
            return lt

    @property
    def gloss(self):
        try:
            gt = retrieve_gloss_words(self)
        except NoNormLineException:
            raise NoGlossLineException('No gloss line available for igt "%s"' % self.id)
        else:
            return gt

    @property
    def trans(self):
        try:
            tt = retrieve_trans_words(self)
        except NoNormLineException:
            raise NoTransLineException('No trans line available for igt "%s"' % self.id)
        else:
            return tt

    # • Morpheme / Sub-Token Tiers -------------------------------------------------------------

    @property
    def glosses(self):
        return glosses(self)


    @property
    def morphemes(self):
        return morphemes(self)



    #===========================================================================
    # ALIGNMENT STUFF
    #===========================================================================


    def heur_align(self, **kwargs):
        return heur_align_inst(self, **kwargs)

    # -------------------------------------------
    # POS TAG MANIPULATION
    # -------------------------------------------

    def add_pos_tags(self, tier_id, tags, tag_method = None):
        """
        Assign a list of pos tags to the tier specified by tier_id. The number of tags
        must match the number of items in the tier.

        :param tier_id: The id for the tier
        :type tier_id: str
        :param tags: A list of POS tag strings
        :type tags: [str]
        """

        # See if we have a pos tier that's already been assigned by this method.
        prev_tier = self.get_pos_tags(tier_id, tag_method=tag_method)

        # And delete it if so.
        if prev_tier: prev_tier.delete()

        # Determine the id of this new tier...
        new_id = gen_tier_id(self, POS_TIER_ID, alignment=tier_id)

        # Find the tier that we are adding tags to.
        tier = self.find(id=tier_id)

        # We assume that the length of the tags we are to add is the same as the
        # number of tokens on the target tier.
        assert len(tier) == len(tags)

        # Create the POS tier
        pt = RGTokenTier(type=POS_TIER_TYPE, id=new_id, alignment=tier_id,
                        attributes={ALIGNMENT:tier_id})

        # And add the metadata for the source (intent) and tagging method
        set_intent_method(pt, tag_method)

        self.append(pt)

        # Go through the words and add the tags.
        for w, tag in zip(tier.items, tags):
            p = RGToken(id=pt.askItemId(), alignment=w.id, text=tag)
            pt.add(p)

    def get_pos_tags(self, tier_id, tag_method = None, morpheme_granularity = False):
        """
        Retrieve the pos tags if they exist for the given tier id...

        :rtype : RGTokenTier
        :param tier_id: Id for the tier to find tags for
        :type tier_id: str
        """

        # Also, if we have specified a tag_method we are looking for, then
        # check the metadata to see if the source is correct.
        filters = []
        if tag_method:
            filters = [lambda x: get_intent_method(x) == tag_method]

        pos_tier = self.find(alignment=tier_id, type=POS_TIER_TYPE, others = filters)

        # If we found a tier, return it with the token methods...
        if pos_tier is not None:
            pos_tier.__class__ = RGTokenTier

            return pos_tier

        # Otherwise, return None...


    def get_lang_sequence(self, tag_method = None, unk_handling=None):
        """
        Retrieve the language line, with as many POS tags as are available.
        """

        # TODO: This is another function that needs reworking
        w_tags = self.get_pos_tags(self.lang.id, tag_method)

        if not w_tags:
            project_creator_except("Language-line POS tags were not found",
                                   "To obtain the language line sequence, please project or annotate the language line.",
                                   tag_method)

        seq = []

        for w in self.lang:
            w_tag = w_tags.find(attributes={ALIGNMENT:w.id})
            if not w_tag:
                if unk_handling == None:
                    tag_str = 'UNK'
                elif unk_handling == 'noun':
                    tag_str = 'NOUN'
                else:
                    raise ProjectionException('Unknown unk_handling attribute')

            else:
                tag_str = w_tag.value()

            w_content = w.value().lower()
            w_content = surrounding_quotes_and_parens(remove_hyphens(w_content))

            w_content = re.sub(punc_re, '', w_content)

            seq.append(POSToken(w_content, label=tag_str))
        return seq

    # • POS Tag Production -----------------------------------------------------

    def tag_trans_pos(self, tagger):
        """
        Run the stanford tagger on the translation words and return the POS tags.

        :param tagger: The active POS tagger model.
        :type tagger: StanfordPOSTagger
        """

        trans_tags = [i.label for i in tagger.tag(tier_text(trans(self)))]

        # Add the generated pos tags to the tier.
        self.add_pos_tags(self.trans.id, trans_tags, tag_method=INTENT_POS_TAGGER)
        return trans_tags

    def classify_gloss_pos(self, classifier_obj=None, **kwargs):
        """
        Run the classifier on the gloss words and return the POS tags.

        :param classifier_obj: the active mallet classifier to classify this language line.
        :type classifier_obj: MalletMaxent
        """
        if classifier_obj is None:
            classifier_obj = MalletMaxent(classifier)

        attributes = {ALIGNMENT:self.gloss.id}

        # Search for a previous run and remove if found...
        prev_tier = self.get_pos_tags(self.gloss.id, tag_method = INTENT_POS_CLASS)

        if prev_tier:
            prev_tier.delete()

        kwargs['prev_gram'] = None
        kwargs['next_gram'] = None

        tags = []

        # Iterate over the gloss tokens...
        for i, gloss_token in enumerate(self.gloss.tokens()):

            # Manually ensure punctuation.
            if re.match('[\.\?"\';/,]+', gloss_token.seq):
                tags.append('PUNC')
            else:

                # TODO: Yet another whitespace issue..
                # TODO: Also, somewhat inelegant forcing it to a string like this...
                gloss_token = re.sub('\s+', '', str(gloss_token))

                # lowercase the token...
                gloss_token = gloss_token.lower()

                #===================================================================
                # Make sure to set up the next and previous tokens for the classifier
                # if they are requested...
                #===================================================================
                if i+1 < len(self.gloss):
                    kwargs['next_gram'] = self.gloss.tokens()[i+1]
                if i-1 >= 0:
                    kwargs['prev_gram'] = self.gloss.tokens()[i-1]

                # The classifier returns a Classification object which has all the weights...
                # obtain the highest weight.
                result = classifier_obj.classify_string(gloss_token, **kwargs)

                if len(result) == 0:
                    best = ['UNK']
                else:
                    best = result.largest()

                # Return the POS tags
                tags.append(best[0])

        self.add_pos_tags(self.gloss.id, tags, tag_method=INTENT_POS_CLASS)
        return tags

    # • POS Tag Projection -----------------------------------------------------


    def project_lang_to_gloss(self, tagmap=None):
        """
        This function serves the purpose of transferring language-line POS tags to the gloss line
         (needed with the CTN data, for instance).

        :type tagmap: TagMap
        :param tag_method:
        """

        lang_tags = self.get_pos_tags(self.lang.id)
        if not lang_tags:
            project_creator_except("No lang-line POS tags found.", None, None)

        # Get the lang-gloss alignment...
        alignment = self.gloss.get_aligned_tokens()

        # Retrieve the tagset mapping.
        if tagmap:
            tm = TagMap(tagmap)

        # Create the POS tier
        new_id = gen_tier_id(self, POS_TIER_ID, alignment=self.gloss.id)

        pt = RGTokenTier(type=POS_TIER_TYPE, id=new_id, alignment=self.gloss.id)


        # And add the metadata for the source (intent) and tagging method
        set_intent_method(pt, MANUAL_POS)

        for lang_tag in lang_tags:
            # Get the gloss word related to this tag. It should share
            # an alignment with the lang_tag...
            gloss_word = self.find(alignment=lang_tag.alignment,
                                   # And it's parent tier should be the GLOSS_WORD_TYPE.
                                   others=[lambda x: hasattr(x, 'tier') and x.tier.type == GLOSS_WORD_TYPE])

            # Do the tag mapping...
            if tagmap:
                postag = tm.get(lang_tag.value())
            else:
                postag = lang_tag.value()


            gpos = RGToken(id=pt.askItemId(), alignment = gloss_word.id, text=postag)
            pt.append(gpos)

        self.append(pt)


    def project_gloss_to_lang(self, tag_method = None, unk_handling=None, classifier=None, posdict=None):
        """
        Project POS tags from gloss words to language words. This assumes that we have
        alignment tags on the gloss words already that align them to the language words.
        """

        lang_tags = self.get_pos_tags(self.lang.id, tag_method=tag_method)
        if lang_tags is not None:
            lang_tags.delete()

        gloss_tags = self.get_pos_tags(self.gloss.id, tag_method=tag_method)

        # If we don't have gloss tags by that creator...
        if not gloss_tags:
            project_creator_except("There were no gloss-line POS tags found",
                                    "Please create the appropriate gloss-line POS tags before projecting.",
                                    tag_method)

        alignment = get_aligned_tokens(gloss(self))

        # If we don't have an alignment between language and gloss line,
        # throw an error.
        if not alignment:
            raise GlossLangAlignException()

        # Get the bilingual alignment from trans to
        # Create the new pos tier...
        pt = RGTokenTier(type=POS_TIER_TYPE,
                         id=gen_tier_id(self, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=self.lang.id),
                         alignment=self.lang.id)

        # Add the metadata as to the source
        set_intent_method(pt, tag_method)
        set_intent_proj_data(pt, gloss_tags, INTENT_ALN_1TO1)

        for g_idx, l_idx in alignment:
            l_w = lang(self)[l_idx - 1]
            g_w = gloss(self)[g_idx - 1]

            # Find the tag associated with this word.
            g_tag = gloss_tags.find(attributes={ALIGNMENT:g_w.id})

            # If no gloss tag exists for this...
            if not g_tag:
                label = 'UNK'

                # If we are not handling unknowns, we could
                # assign it "UNK", OR we could just skip it
                # and leave it unspecified.
                # Here, we choose to skip.
                if unk_handling is None:
                    continue

                elif unk_handling == 'keep':
                    pass

                # If we are doing the "Noun" method, then we
                # replace all the unknowns with "NOUN"
                elif unk_handling == 'noun':
                    label = 'NOUN'

                # Finally, we can choose to run the classifier on
                # the unknown gloss words.
                elif unk_handling == 'classify':
                    kwargs = {'posdict':posdict}    # <-- Initialize the new kwargs for the classifier.
                    if not classifier:
                        raise ProjectionException('To project with a classifier, one must be provided.')

                    # Set up for the classifier...
                    kwargs['prev_gram'] = ''
                    kwargs['next_gram'] = ''

                    if g_idx > 1:
                        kwargs['prev_gram'] = self.gloss.get_index(g_idx-1).value()
                    if g_idx < len(self.gloss):
                        kwargs['next_gram'] = self.gloss.get_index(g_idx+1).value()

                    # Replace the whitespace in the gloss word for error
                    # TODO: Another whitespace replacement handling.
                    g_content = re.sub('\s+','', g_w.value())


                    label = classifier.classify_string(g_content, **kwargs).largest()[0]

                else:
                    raise ProjectionException('Unknown unk_handling method "%s"' % unk_handling)

            else:
                label = g_tag.value()

            pt.add(RGToken(id=pt.askItemId(), alignment = l_w.id, text=label))

        self.append(pt)



    def project_trans_to_lang(self, aln_method=None, tag_method=None):
        """
        Project POS tags from the translation line directly to the language
        line. This assumes that we have a bilingual alignment between
        translation words and language words already.

        """

        # Get the alignment between translation and language lines
        ta_aln = self.get_bilingual_alignment(self.trans.id, self.lang.id, aln_method=aln_method)

        # Get the trans tags...
        trans_tags = self.get_pos_tags(self.trans.id, tag_method=tag_method)

        if not ta_aln:
            raise ProjectionException("No translation-language-line alignment was found for instance \"{}\". Not projecting.".format(self.id))


        # Create the new pos tier...
        pos_id = gen_tier_id(self, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=self.lang.id)
        pt = RGTokenTier(type=POS_TIER_TYPE, id=pos_id, alignment=self.lang.id)

        # Add the metadata about the source of the tags.
        set_intent_method(pt, INTENT_POS_PROJ)
        set_intent_proj_data(pt, trans_tags, ta_aln.type)

        for t_i, l_i in ta_aln:
            t_word = self.trans.get_index(t_i)
            t_tag = trans_tags[t_i-1]

            l_word = self.lang.get_index(l_i)

            pt.add(RGToken(id=pt.askItemId(), alignment = l_word.id, text = str(t_tag)))

        self.append(pt)

    # • Translation Line Parsing -----------------------------------------------
    def parse_translation_line(self, parser, pt=False, dt=False):
        """
        Parse the translation line in order to project phrase structure.

        :param parser: Initialized StanfordParser
        :type parser: StanfordParser
        """
        assert pt or dt, "At least one of pt or dt should be true."

        PARSELOG.debug('Attempting to parse translation line of instance "{}"'.format(self.id))

        # Replace any parens in the translation line with square brackets, since they
        # will cause problems in the parsing otherwise.

        trans_text = tier_text(trans(self)).replace('(', '[')
        trans_text = trans_text.replace(')',']')

        result = parser.parse(trans_text)

        PARSELOG.debug('Result of translation parse: {}'.format(result.pt))

        if pt and result.pt:
            create_pt_tier(self, result.pt, trans(self), parse_method=INTENT_PS_PARSER)
        if dt and result.dt:
            create_dt_tier(self, result.dt, trans(self), parse_method=INTENT_DS_PARSER)


#===============================================================================
# Items
#===============================================================================

class RGItem(Item, FindMixin):
    """
    Subclass of the xigt core "Item."
    """

    def __init__(self, **kwargs):

        new_kwargs = {key : value for key, value in kwargs.items() if key not in ['index', 'start', 'stop']}

        super().__init__(**new_kwargs)

        self.start = kwargs.get('start')
        self.stop = kwargs.get('stop')

    def copy(self, parent=None):
        """
        Part of a recursive deep-copy function. Faster to implement here specifically than calling
        copy.deepcopy.

        :param parent:
        :type parent:
        """
        new_item = RGItem(id=self.id, type=self.type,
                            alignment=copy.copy(self.alignment),
                            content=copy.copy(self.content),
                            segmentation=copy.copy(self.segmentation),
                            attributes=copy.deepcopy(self.attributes),
                            text=copy.copy(self.text),
                            tier=parent)
        return new_item


    @property
    def tier(self):
        """
        :rtype : RGTier
        """
        return super().tier

    @property
    def igt(self):
        """
        :rtype : RGIgt
        """
        return super().igt


class RGLine(RGItem):
    """
    Subtype for "lines" (raw or normalized)
    """
    pass

class RGPhrase(RGItem):
    """
    Subtype for phrases...
    """


class RGToken(RGItem):
    """
    A subtype of item for items that can be considered tokens.
    """

    def __init__(self, **kwargs):
        RGItem.__init__(self, **kwargs)


class RGWord(RGToken):
    """
    A specific type of item for handling words
    """

class RGMorph(RGToken):
    """
    A specific type of item for handling sub-word-level items.
    """

    def __init__(self, words=list, **kwargs):
        RGItem.__init__(self, **kwargs)
        self._words = words


class RGBilingualAlignment(RGItem):
    """
    Item to hold a bilingual alignment.
    """
    def __init__(self, source=None, target=None, **kwargs):
        super().__init__(**kwargs)

        if source:
            self.attributes[SOURCE_ATTRIBUTE] = source
        if target:
            self.attributes[TARGET_ATTRIBUTE] = target

    def add_tgt(self, tgt):
        if self.attributes[TARGET_ATTRIBUTE]:
            self.attributes[TARGET_ATTRIBUTE] += ','+tgt
        else:
            self.attributes[TARGET_ATTRIBUTE] = tgt


    @property
    def source(self):
        if 'source' in self.attributes:
            return self.attributes[SOURCE_ATTRIBUTE]
        else:
            return None

    @property
    def target(self):
        if 'target' in self.attributes:
            return self.attributes[TARGET_ATTRIBUTE]
        else:
            return None


#===============================================================================
# Tiers
#===============================================================================


class RGTier(Tier, RecursiveFindMixin):

    def copy(self, parent=None):
        """
        Perform a deep copy.
        """

        new_t = RGTier(id=self.id, type=self.type,
                    alignment=copy.copy(self.alignment),
                    content=copy.copy(self.content),
                    segmentation=copy.copy(self.segmentation),
                    attributes=copy.deepcopy(self.attributes),
                    metadata=copy.copy(self.metadata),
                    items=None, igt=parent)

        for item in self.items:
            new_t.add(item.copy(parent=new_t))

        return new_t

    def add(self, obj):
        """
        Override the default add method to place indices on
        elements.
        """
        obj.index = len(self)+1
        Tier.append(self, obj)

    def askItemId(self):
        return gen_item_id(self.id, len(self))

    def askIndex(self):
        return len(self.items)+1

    def text(self, remove_whitespace_inside_tokens = True, return_list = False):
        """
        Return a whitespace-delimeted string consisting of the
        elements of this tier. Default to removing whitespace
        that occurs within a token.
        """
        tokens = [str(i) for i in self.tokens()]
        if remove_whitespace_inside_tokens:

            # TODO: Another whitespace replacement handling
            tokens = [re.sub('\s+','',i) for i in tokens]

        if return_list:
            return tokens
        else:
            return ' '.join(tokens)

    def tokens(self):
        """
        Return a list of the content of this tier.
        """
        return [Token(i.value(), index=i.index) for i in self]

    @property
    def index(self):
        """
        Return the integer index (from zero) of this element in its
        parent tier.
        """
        return self.igt.tiers.index(self)

    def delete(self):
        """
        Remove this tier from its parent, and refresh
        the index to notify the instance of its removal.
        """
        self.igt.remove(self)

    @property
    def igt(self):
        """
        :rtype : RGIgt
        """
        return super().igt



class RGLineTier(RGTier):
    """
    Tier type that contains only "lines"
    """

class RGPhraseTier(RGTier):
    """
    Tier type that contains phrases.
    """

class RGTokenTier(RGTier):
    """
    Tier type that can be considered to contain tokens.
    """

    def get_aligned_tokens(self):
        """
        Function to return the alignment indices between this tier and another
        it is aligned with.
        """

        a = Alignment()
        for item in self:
            ia = item.alignment
            if ia:
                aligned_w = self.igt.find(id=ia)
                a.add((item.index, aligned_w.index))
        return a

    def __iter__(self):
        """

        :rtype : RGToken
        """
        return super().__iter__()

    def set_aligned_tokens(self, tgt_tier, aln, aln_method=None):
        # FIXME: This method does not appear to be called anywhere but unit tests... is it still needed?
        """
        Given an alignment, set the alignments correspondingly.

        NOTE: This function should only be used for the alignment="" attribute, which is
              reserved for aligning items of the same supertype. (e.g. morphemes and glosses)
              and SHOULD NOT be used for aligning, say, gloss morphs to the translation line.
        """
        # First, set our alignment target to the provided
        # tier.
        self.alignment = tgt_tier.id

        # Set the alignment method if we have it specified.
        #self.attributes['']
        set_intent_method(self, aln_method)

        # Also, blow away any previous alignments.
        for item in self:
            del item.attributes[ALIGNMENT]


        # Next, select the items from our tier (src) and tgt tier (tgt)
        # and align them.
        for src_i, tgt_i in aln:
            # Get the tokens (note that the indexing is from 1
            # when using alignments, as per GIZA standards)
            src_token = self[src_i-1]
            tgt_token = tgt_tier[tgt_i-1]

            src_token.alignment = tgt_token.id


class RGPhraseStructureTier(RGTier):
    """
    Specialized tier that will hold a phrase structure tree, or read it if it doesn't exist.
    """
    def __init__(self, pt=None, **kwargs):
        RGTier.__init__(self, **kwargs)
        self._tree = pt

    @property
    def tree(self):
        """
        If the tier already has a IdTree, simply return it. Otherwise, create it by reading the Xigt.
        """
        if self._tree is None:
            self._tree = read_pt(self.igt)

        return self._tree


class RGWordTier(RGTokenTier):
    """
    Tier type that contains words.
    """

    @classmethod
    def from_string(cls, string, **kwargs):
        wt = cls(**kwargs)
        for w in intent.utils.token.tokenize_string(string):
            wi = RGToken(id=wt.askItemId(), text=str(w))
            wt.add(wi)
        return wt

    def morph_tier(self, type, id, aln_attribute):
        """
        Given the "words" in this tier, segment them.
        """

        mt = RGMorphTier(id=id, attributes={aln_attribute:self.id}, type=type)

        # Go through each word...
        for word in self:

            morphs = intent.utils.token.tokenize_item(word, intent.utils.token.morpheme_tokenizer)

            for morph in morphs:
                # If there is only one morph in the tokenization, don't bother with the indexing, just
                # use the id.
                if len(morphs) == 1:
                    aln_str = word.id
                else:
                    aln_str = create_aln_expr(word.id, morph.start, morph.stop)

                rm = RGMorph(id=mt.askItemId(),
                             attributes={aln_attribute: aln_str},
                             index=mt.askIndex())
                mt.add(rm)

        return mt



class RGMorphTier(RGTokenTier):
    """
    Tier type that contains morphemes.
    """






#===============================================================================
# Other Metadata
#===============================================================================


class RGMetadata(Metadata): pass

class RGMeta(Meta): pass


#===============================================================================
# • Basic Functions
#===============================================================================
def create_aln_expr(id, start=None, stop=None):
    """
    Create an alignment expression, such as ``n2[5:8]`` or ``tw1`` given an id, and start/stop range.

    :param id: ID with which to align
    :type id: str
    :param start: Range at which to start
    :type start: int
    :param stop: Range at which to stop
    :type stop: int
    """

    if start is None and stop is None:
        return id
    elif start is not None and stop is not None:
        return '%s[%d:%d]' % (id, start, stop)
    else:
        raise Exception('Invalid alignment expression request')


#===============================================================================
# • Phrase Tier Creation ---
#===============================================================================

def retrieve_trans_phrase(inst):
    """
    Retrieve the translation phrase tier if it exists, otherwise create it. (Making
    sure to align it with the language phrase if it is present)

    :param inst: Instance to search
    :type inst: RGIgt
    """
    tpt = retrieve_phrase_tier(inst, ODIN_TRANS_TAG, TRANS_PHRASE_ID, TRANS_PHRASE_TYPE)

    # Add the alignment with the language line phrase if it's not already there.
    if ALIGNMENT not in tpt.attributes:
        try:
            lpt = retrieve_lang_phrase_tier(inst)
            tpt.attributes[ALIGNMENT] = lpt.id
            tpt[0].attributes[ALIGNMENT] = lpt[0].id
        except MultipleNormLineException as mnle:
            pass
        except NoNormLineException as nlle:
            pass

    return tpt

def retrieve_lang_phrase_tier(inst):
    """
    Retrieve the language phrase if it exists, otherwise create it.

    :param inst: Instance to search
    :type inst: RGIgt
    """
    return retrieve_phrase_tier(inst, ODIN_LANG_TAG, LANG_PHRASE_ID, LANG_PHRASE_TYPE)

def retrieve_phrase_tier(inst, tag, id, type):
    """
    Retrieve a phrase for the given tag, with the provided id and type.

    :param inst: Instance to retrieve the elements from.
    :type inst: RGIgt
    :param tag: 'L', 'G' or 'T'
    :type tag: str
    :param id:
    :type id: str
    :param type:
    :type type: str
    """

    # TODO FIXME: VERY kludgy and unstable...
    f = lambda x: tag in aligned_tags(x)
    pt = find_in_obj(inst, type=type, others=[f])

    if pt is None:
        n = get_normal_tier(inst)
        # Get the normalized line
        l = retrieve_normal_line(inst, tag)

        # -------------------------------------------
        # Create the phrase tier, and add a single phrase item.
        pt = RGPhraseTier(id=id, type=type, content=n.id)

        # -------------------------------------------
        # Propagate the judgment attribute on the line to the phrase item
        phrase_attributes = {}
        old_judgment = l.attributes.get(ODIN_JUDGMENT_ATTRIBUTE)
        if l.attributes.get(ODIN_JUDGMENT_ATTRIBUTE) is not None:
            phrase_attributes[ODIN_JUDGMENT_ATTRIBUTE] = old_judgment

        pt.add(RGPhrase(id=pt.askItemId(), content=l.id, attributes=phrase_attributes))
        inst.append(pt)
    else:
        pt.__class__ = RGPhraseTier

    return pt

#===============================================================================
# • Word Tier Creation ---
#===============================================================================

def create_words_tier(cur_item, word_id, word_type, aln_attribute = SEGMENTATION, tokenizer=whitespace_tokenizer):
    """
    Create a words tier from an ODIN line type item.

    :param cur_item: Either a phrase item or a line item to tokenize and create words form.
    :type cur_item: RGItem
    :param word_id: The ID for this tier.
    :type word_id: str
    :param word_type: Tier type for this tier.
    :type word_type: str

    :rtype: RGWordTier
    """

    # For the edge case in which the gloss line is defined, but empty.
    if cur_item.value() is None or not cur_item.value().strip():
        words = []
    else:
        # Tokenize the words in this phrase...
        words = intent.utils.token.tokenize_item(cur_item, tokenizer=tokenizer)

    # Create a new word tier to hold the tokenized words...
    wt = Tier(id = word_id, type=word_type, attributes={aln_attribute:cur_item.tier.id}, igt=cur_item.igt)

    for w in words:
        # Create a new word that is a segmentation of this tier.
        rw = RGWord(id=gen_item_id(wt.id, len(wt)), attributes={aln_attribute:create_aln_expr(cur_item.id, w.start, w.stop)}, tier=wt, start=w.start, stop=w.stop)
        wt.append(rw)

    return wt

def retrieve_trans_words(inst, create=True):
    """
    Retrieve the translation words tier from an instance.

    :type inst: RGIgt
    :rtype: RGWordTier
    """

    # Get the translation phrase tier
    tpt = retrieve_trans_phrase(inst)

    # Get the translation word tier
    twt = find_in_obj(inst,
                type=TRANS_WORD_TYPE,
                segmentation=tpt.id)

    if twt is None and create:
        twt = create_words_tier(tpt[0], TRANS_WORD_ID, TRANS_WORD_TYPE, tokenizer=sentence_tokenizer)
        inst.append(twt)

    return twt

def retrieve_lang_words(inst, create=True):
    """
    Retrieve the language words tier from an instance

    :type inst: RGIgt
    :rtype: RGWordTier
    """
    # Get the lang phrase tier
    lpt = retrieve_lang_phrase_tier(inst)

    # Get the lang word tier
    lwt = find_in_obj(inst, type=LANG_WORD_TYPE, segmentation=lpt.id)

    if lwt is None and create:
        lwt = create_words_tier(lpt[0], LANG_WORD_ID, LANG_WORD_TYPE)
        inst.append(lwt)

    return lwt

#===============================================================================
# • Finding References ---
#===============================================================================

def odin_ancestor(obj):
    # ODIN_LOG.debug("Looking up the odin ancestor for {}".format(str(obj)))
    # If we are at an ODIN item, return.

    if isinstance(obj, Item) and obj.tier.type == ODIN_TYPE:
        return obj

    # An Igt instance can't have a tier ancestor.
    elif isinstance(obj, Igt):
        return None

    # Also, an ODIN tier can't get a specific item...
    elif isinstance(obj, Tier) and obj.type == ODIN_TYPE:
        return None

    else:


        if SEGMENTATION in obj.attributes:
            ref_attr = SEGMENTATION
        elif CONTENT in obj.attributes:
            ref_attr = CONTENT
        elif ALIGNMENT in obj.attributes:
            ref_attr = ALIGNMENT
        elif DS_DEP_ATTRIBUTE in obj.attributes:
            ref_attr = DS_DEP_ATTRIBUTE
        else:
            return None

        # If this item is a tier, we would like to follow a random object
        if isinstance(obj, Tier):
            if len(obj) == 0:
                id = obj.attributes[ref_attr]
            else:
                id = [ids(i.attributes[ref_attr])[0] for i in obj if ref_attr in i.attributes][0]
        elif isinstance(obj, Item):
            id = ids(obj.attributes[ref_attr])[0]
        else:
            raise Exception

        item = find_in_obj(obj.igt, id=id)
        if item is None:
            return None
        else:
            return odin_ancestor(item)



def aligned_tags(obj):
    """
    Given an object, return the tags that it is ultimately aligned with.

    :param obj:
    """

    a = odin_ancestor(obj)
    if a:
        return a.attributes['tag'].split('+')
    else:
        return []


def retrieve_gloss_words(inst, create=True):
    """
    Given an IGT instance, create the gloss "words" and "glosses" tiers.

    1. If a "words" type exists, and it's contents are the gloss line, return it.
    2. If it does not exist, tokenize the gloss line and return it.
    3. If there are NO tokens on the gloss line for whatever reason... Return None.

    :param inst: Instance which to create the tiers from.
    :type inst: RGIgt
    :rtype: RGWordTier
    """

    # 1. Look for an existing words tier that aligns with the normalized tier...
    wt = find_in_obj(inst, type=GLOSS_WORD_TYPE,
                   # Add the "others" to find only the "glosses" tiers that
                   # are at the word level...

                   # TODO FIXME: Find more elegant solution
                   others=[lambda x: is_word_level_gloss(x),
                           lambda x: ODIN_GLOSS_TAG in aligned_tags(x) ])

    # 2. If it exists, return it. Otherwise, look for the glosses tier.
    if wt is None and create:
        n = get_normal_tier(inst)
        g_n = retrieve_normal_line(inst, ODIN_GLOSS_TAG)

        # If the value of the gloss line is None, or it's simply an empty string...
        if g_n is None or g_n.value() is None or not g_n.value().strip():
            raise EmptyGlossException()
        else:
            wt = create_words_tier(retrieve_normal_line(inst, ODIN_GLOSS_TAG), GLOSS_WORD_ID,
                                   GLOSS_WORD_TYPE, aln_attribute=CONTENT)

        # Set the "gloss type" to the "word-level"
        add_word_level_info(wt, INTENT_GLOSS_WORD)
        inst.append(wt)
    elif wt is not None:
        wt.__class__ = RGWordTier
    else:
        return None


    # If we have alignment, we can remove the metadata, because
    # that indicates the type for us.
    if wt.alignment is not None:
        remove_word_level_info(wt)

    return wt

def retrieve_normal_line(inst, tag):
    """
    Retrieve a normalized line from the instance ``inst1`` with the given ``tag``.

    :param inst: Instance to retrieve the normalized line from.
    :type inst: RGIgt
    :param tag: {'L', 'G', or 'T'}
    :type tag: str

    :rtype: RGPhrase
    """

    n = get_normal_tier(inst)

    lines = [l for l in n if tag in l.attributes[ODIN_TAG_ATTRIBUTE].split('+')]

    if len(lines) < 1:
        raise NoNormLineException('No normalized line found for tag "{}" in instance "{}"'.format(tag, inst.id))
    elif len(lines) > 1:
        raise MultipleNormLineException('Multiple normalized lines found for tag "{}" in instance {}'.format(tag, inst.id))
    else:
        return lines[0]


def intervening_characters(item_a, item_b):
    """
    Given two items that segment the same line, return the characters that
    occur between the two.

    :param item_a: First item that segments
    :param item_b: Second item that segments
    """

    # Assert that both items segment the same ODIN line
    assert odin_ancestor(item_a) == odin_ancestor(item_b)

    ancestor = odin_ancestor(item_a)

    # Get the spans of the two items.
    span_a = odin_span(item_a)
    span_b = odin_span(item_b)

    # Take the last index of the first item, and the
    # first index of the second item, and retrieve
    # the string from inside
    span_a_last = span_a[-1][-1]
    span_b_first = span_b[0][0]

    return ancestor.value()[span_a_last:span_b_first]


#===============================================================================
# Alignment Utilities ---
#===============================================================================

def word_align(this, other):
    """

    :param this:
    :type this:
    :param other:
    :type other:
    """

    if len(this) != len(other):
        raise GlossLangAlignException('Gloss and language lines could not be auto-aligned for igt "%s"' % this.igt.id)
    else:
        # Note on the tier the alignment
        this.alignment = other.id

        # Align the words 1-to-1, left-to-right
        for my_word, their_word in zip(this, other):
            my_word.alignment = their_word.id

        # Remove the word type metadata.
        remove_word_level_info(this)
        remove_word_level_info(other)

def morph_align(gloss_tier, morph_tier):
    """
    Given the gloss morphemes and language morphemes, add
    the alignment attributes to the gloss line tokens.

    :param gloss_tier:
    :param morph_tier:
    """
    # First, set the alignment...
    gloss_tier.alignment = morph_tier.id

    # Let's count up how many morphemes there are
    # for each word on the translation line...
    lang_word_dict = defaultdict(list)

    for morph in morph_tier:
        # Add this morpheme to the dictionary, so we can keep
        # count of how many morphemes align to a given word.
        lang_word_dict[find_lang_word(gloss_tier.igt, morph).id].append(morph)

    # FIXME: Somewhere here, we are adding alignment to morphemes instead of glosses.

    # Now, iterate over our morphs.
    for i, gloss in enumerate(gloss_tier):

        # Find the word that this gloss aligns to...
        gloss_word = find_gloss_word(gloss_tier.igt, gloss)
        word_id = gloss_word.alignment # And the id of the lang word

        # Next, let's see what unaligned morphs there are
        aligned_lang_morphs = lang_word_dict[word_id]

        # If we don't have any aligned morphs,
        # just skip.
        if len(aligned_lang_morphs) >= 1:
            # If this isn't the last morph, try and see if we are
            # at a morpheme boundary...
            if i < len(gloss_tier)-1:
                split_chars = intervening_characters(gloss_tier[i], gloss_tier[i+1]).strip()

                # If the character following this morph is a morpheme bounadry
                # character or whitespace, then "pop" the morph. Otherwise,
                # don't pop it.
                if len(aligned_lang_morphs) == 1:
                    lang_morph = aligned_lang_morphs[0]
                elif split_chars == '' or split_chars in morpheme_boundary_chars:
                    lang_morph = aligned_lang_morphs.pop(0)
                else:
                    lang_morph = aligned_lang_morphs[0]

            # Otherwise, we are at the last gloss. Just assign it to the
            # last remaining lang morph.
            else:
                lang_morph = aligned_lang_morphs.pop(0)

            gloss.alignment = lang_morph.id


        # # If there's only one morph left, align with that.
        # if len(aligned_lang_morphs) == 1:
        #     gloss.alignment = aligned_lang_morphs[0].id


        # # If there's more, pop one off the beginning of the list and use that.
        # # This will cause subsequent morphs to align to the rightmost morph
        # # that also aligns to the same word
        # elif len(aligned_lang_morphs) > 1:
        #     lang_morph = aligned_lang_morphs.pop(0)
        #     gloss.alignment = lang_morph.id

#===============================================================================
# • Searching ---
#===============================================================================

def find_lang_word(inst, morph):
    """
    Given a morph that segments the language line, find its associated word.

    :param morph: The morpheme to find the aligned word for.
    :type morph: RGMorph

    :rtype: RGWord
    """
    ids = set(ref.ids(morph.segmentation))
    assert len(ids) == 1, "A morph should not segment more than one word"

    return inst.find(id = ids.pop())


def odin_span(item):
    """
    Follow this item's segmentation all the way
    back to the raw odin item it originates from.

    :param inst1: Instance to pull from
    :type inst1: RGIgt
    :param item: RGItem
    :type item: Item to trace the alignment for.
    """

    # The base case, if we have arrived at an ODIN_TYPE tier
    # already, we should return the full span of the item.
    if item.tier.type == ODIN_TYPE:
        return [(0, len(item.value()))]

    else:
        # Otherwise, we have two options. We are at an item which:
        # (1) has content/segmentation of a bare ID ("w2")
        # (2) has content/segmentation with a span ("w2[2:5]")

        # Select the expression which indicates how we will search..
        aln_expr = item.attributes.get(CONTENT)
        if not aln_expr:
            aln_expr = item.attributes.get(SEGMENTATION)

        spans = []

        for aligned_object, span in resolve_objects(item.igt, aln_expr):
            if span is None:
                spans.extend(odin_span(aligned_object))
            else:
                aln_start, aln_stop = span
                for start, stop in odin_span(aligned_object):
                    spans.extend([(start+aln_start, start+aln_stop)])

        return spans





def x_contains_y(inst, x_item, y_item):
    return x_span_contains_y(odin_span(x_item), odin_span(y_item))

def x_span_contains_y(x_spans, y_spans):
    """
    Return whether all elements of y_spans are contained by some elements of x_spans

    :param x_spans:
    :type x_spans:
    :param y_spans:
    :type y_spans:
    """



    for i, j in y_spans:
        match_found = False

        for m, n in x_spans:
            if i >= m and j <= n:
                 match_found = True
                 break

        # If this particular x_span found
        # a match, keep looking.
        if match_found:
            continue

        # If we find an element that doesn't
        # have a match, return false.
        else:
            return False

    # If we have reached the end of both loops, then
    # all elements match.
    return True


def find_gloss_word(inst, morph):
    """
    Find the gloss word to which this gloss morph is aligned. This will search the word-level "glosses" tier to
    find overlaps.

    :param morph: Gloss line morph to find alignment for.
    :type morph: RGMorph

    :rtype: RGWord
    """

    for g in gloss(inst):

        if x_contains_y(inst, g, morph):
            return g

    # If we reached this far, there is no gloss word that contains this
    # morph.
    return None


def follow_alignment(inst, id):
    """
    If the given ID is aligned to another item, return that other item. If that item
    is aligned to another item, return THAT item's ID, and so on.
    """

    # Return none if this id isn't found.
    found = inst.find(id)
    w = None

    if not found:
        return None

    # Look to see if there's an alignment attribute.
    if found.alignment:
        return follow_alignment(inst, found.alignment)

    # If there's not a word that this is a part of,
    if w:
        return follow_alignment(inst, w.id)

    else:
        return found

def add_word_level_info(obj, val):
    set_meta_attr(obj, INTENT_EXTENDED_INFO, INTENT_TOKEN_TYPE, val, metadata_type=INTENT_META_TYPE)

def remove_word_level_info(obj):
    del_meta_attr(obj, INTENT_EXTENDED_INFO, INTENT_TOKEN_TYPE)

def get_word_level_info(obj):
    return find_meta_attr(obj, INTENT_EXTENDED_INFO, INTENT_TOKEN_TYPE)

def is_word_level_gloss(obj):
    """
    Return true if this item is a "word-level" tier. (That is, it should
    either have explicit metadata stating such, or its alignment will be
    with a word tier, rather than a morphemes tier)

    :param obj:
    :returns bool:
    """

    if not isinstance(obj, Tier):
        return False

    # If we have explicit metadata that says we are a word,
    # return true.
    if get_word_level_info(obj) == INTENT_GLOSS_WORD:
        return True

    # Otherwise, check and see if we are aligned with a
    else:
        a = find_in_obj(obj.igt, id=obj.alignment)
        return (a is not None) and (a.type == WORDS_TYPE)


#===============================================================================
# Sorting ---
#===============================================================================

def sort_corpus(xc: XigtCorpus):
    """
    Sort the corpus in-place.
    """
    for inst in xc:
        inst.sort_tiers()



#===============================================================================
# • Cleaning ---
#===============================================================================


def strip_alignment(inst):
    strip_pos(inst)
    for at in inst.findall(type=ALN_TIER_TYPE):
        at.delete()


def strip_pos(inst):
    for pt in inst.findall(type=POS_TIER_TYPE):
        pt.delete()


from intent.trees import Terminal, DepTree, DepEdge, build_dep_edges
from .search import *
from .igtutils import remove_hyphens, surrounding_quotes_and_parens, punc_re
from .alignment import heur_align_inst, set_bilingual_alignment