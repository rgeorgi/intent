"""
Subclassing of the xigt package to add a few convenience methods.
"""

#===============================================================================
# Logging
#===============================================================================

import logging
import re
import copy
import string


from xigt.model import XigtCorpus, Igt, Item, Tier
from xigt.metadata import Metadata, Meta
from xigt.consts import ALIGNMENT, SEGMENTATION, CONTENT
from intent.igt.metadata import add_meta, find_meta_attr, del_meta_attr, set_intent_method, get_intent_method, \
    set_intent_proj_data
from xigt import ref




# Set up logging ---------------------------------------------------------------
PARSELOG = logging.getLogger(__name__)

# XIGT imports -----------------------------------------------------------------
from xigt.codecs import xigtxml

# INTERNAL imports -------------------------------------------------------------
from .igtutils import merge_lines, clean_lang_string, clean_gloss_string,\
    clean_trans_string, remove_hyphens, surrounding_quotes_and_parens, punc_re, rgencode, rgp, resolve_objects

from .consts import *

import intent.utils.token
from intent.utils.env import c
from intent.alignment.Alignment import Alignment, heur_alignments
from intent.utils.token import Token, POSToken
from intent.interfaces.giza import GizaAligner
from intent.utils.dicts import DefaultOrderedDict

# Other imports ----------------------------------------------------------------
from collections import defaultdict





#===============================================================================
# Exceptions
#===============================================================================

class RGXigtException(Exception): pass

# • Format Exceptions ------------------------------------------------------------

class XigtFormatException(RGXigtException): pass
class NoNormLineException(XigtFormatException): pass
class MultipleNormLineException(XigtFormatException): pass

class NoTransLineException(XigtFormatException): pass
class NoLangLineException(XigtFormatException):	pass
class NoGlossLineException(XigtFormatException): pass

class NoODINRawException(XigtFormatException):	pass

# • Alignment and Projection Exceptions ------------------------------------------

class GlossLangAlignException(RGXigtException):	pass

class ProjectionException(RGXigtException): pass

class ProjectionTransGlossException(ProjectionException): pass

class PhraseStructureProjectionException(RGXigtException): pass


def project_creator_except(msg_start, msg_end, created_by):

    if created_by:
        msg_start += ' by the creator "%s".' % created_by
    else:
        msg_start += '.'
    raise ProjectionException(msg_start + ' ' + msg_end)

#===============================================================================
# Mixins
#===============================================================================



def ref_match(o, target_ref, ref_type):
    if hasattr(o, ref_type):
        my_ref = getattr(o, ref_type)
        if my_ref and target_ref in ref.ids(my_ref):
            return True
    return False

def seg_match(seg): return lambda o: ref_match(o, seg, SEGMENTATION)
def cnt_match(cnt): return lambda o: ref_match(o, cnt, CONTENT)
def aln_match(aln): return lambda o: ref_match(o, aln, ALIGNMENT)

def type_match(type): return lambda o: o.type == type
def id_match(id): return lambda o: o.id == id
def id_base_match(id_base): return lambda o: get_id_base(o.id) == id_base
def attr_match(attr): return lambda o: set(attr.items()).issubset(set(o.attributes.items()))

class FindMixin():
    """
    Extension of the recursive search for non-iterable elements.
    """

    # FindMixin objects should have an index.
    index = None

    def find_self(self, filters=list):
        """
        Check to see if this object matches all of the filter functions in filters.

        :param filters: List of functions to apply to this object. All filters have a logical and
                        applied to them.
        :type filters: list
        """

        assert len(filters) > 0, "Must have selected some attribute to filter."

        # Iterate through the filters...
        for filter in filters:
            if not filter(self): # If one evaluates to false...
                return None      # ..we're done. Exit with "None"

        # If we make it through all the iteration, we're a match. Return.
        return self

    def _build_filterlist(self, **kwargs):
        filters = []
        for kw, val in kwargs.items():
            if kw == 'id':
                filters += [id_match(val)]
            elif kw == 'content':
                filters += [cnt_match(val)]
            elif kw == 'segmentation':
                filters += [seg_match(val)]
            elif kw == 'id_base':
                filters += [id_base_match(val)]
            elif kw == 'attributes':
                filters += [attr_match(val)]
            elif kw == 'type':
                filters += [type_match(val)]

            elif kw == 'others': # Append any other filters...
                filters += val
            else:
                raise ValueError('Invalid keyword argument "%s"' % kw)
        return filters

    def find(self, **kwargs):
        return self.find_self(self._build_filterlist(**kwargs))

    def findall(self, **kwargs):
        found = self.find_self(self._build_filterlist(**kwargs))
        if found:
            return [found]
        else:
            return []

class RecursiveFindMixin(FindMixin):

    # Define the FindMixin as iterable,
    # but don't implement the class.
    def __iter__(self): pass

    def find(self, **kwargs):
        """
        Generic find function for non-iterable elements. NOTE: This version stops on the first match.

        :param id: id of an element to find, or None to search by attribute.
        :type id: str
        :param attributes: key:value pairs that are an inclusive subset of those found in the desired item.
        :type attributes: dict
        """
        if super().find(**kwargs) is not None:
            return self
        else:
            found = None
            for child in self:
                found = child.find(**kwargs)
                if found is not None:
                    break
            return found

    def findall(self, **kwargs):
        """
        Find function that does not terminate on the first match.
        """
        found = []
        if super().find(**kwargs) is not None:
            found = [self]

        for child in self:
            found += child.findall(**kwargs)

        return found


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
            w = tier.igt.find(id=aln)
            n = IdTree(node.value(), [Terminal(w.value(), w.index)])

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


def gen_item_id(id_base, num):
    return '{}{}'.format(id_base, num+1)

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
    num_tiers = len(inst.findall(others=filters))


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
    if num_tiers > 0:
        letters = string.ascii_lowercase
        assert num_tiers < 26, "More than 26 alternative analyses not currently supported"
        id_str += '_{}'.format(letters[num_tiers])

    return id_str


def get_id_base(id_str):
    """
    Return the "base" of the id string. This should either be everything leading up to the final numbering, or a hyphen-separated letter.

    :param id_str:
    :type id_str:
    """
    s = re.search('^(\S+?)(?:[0-9]+|-[a-z])?$', id_str).group(1)
    return s

# ===============================================================================


class RGCorpus(XigtCorpus, RecursiveFindMixin):

    def askIgtId(self):
        return gen_item_id('i', len(self.igts))

    def __len__(self):
        return len(self._list)

    def copy(self, limit=None):
        new_c = RGCorpus(id=self.id, attributes=copy.deepcopy(self.attributes), metadata=copy.copy(self.metadata), igts=None)

        for i, igt in enumerate(self.igts):
            new_c.append(igt.copy(parent=new_c))

            if limit and i >= limit:
                break

        return new_c

    @classmethod
    def from_txt(cls, text, require_trans = True, require_gloss = True, require_lang = True, require_1_to_1 = True, limit = None):
        """
        Read in a odin-style textfile to create the xigt corpus.

        """
        # Initialize the corpus
        xc = cls()

        # Replace invalid characters...
        _illegal_xml_chars_RE = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')
        data = re.sub(_illegal_xml_chars_RE, ' ', text)

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
                i = RGIgt.fromString(inst_txt, corpus=xc, require_1_to_1=require_1_to_1, idnum=inst_num)
            except GlossLangAlignException as glae:
                PARSELOG.warn('Gloss and language could not be automatically aligned for instance "%s". Skipping' % gen_item_id('i', inst_num))
                continue

            # Try to get the translation line. ---------------------------------
            try:
                hastrans = i.trans
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

    @classmethod
    def load(cls, path, basic_processing = False):
        xc = xigtxml.load(path)
        xc.__class__ = RGCorpus
        xc._finish_load()

        # If asked, we will also do some
        # basic-level enrichment...
        if basic_processing:
            for inst in xc:
                inst.basic_processing()
                inst.add_gloss_lang_alignments()

        return xc

    def _finish_load(self):
        # Now, convert all the IGT instances to RGIgt instances.
        for igt in self.igts:
            igt.__class__ = RGIgt

            for tier in igt.tiers:
                tier.__class__ = RGTier

                for i, item in enumerate(tier):
                    item.__class__ = RGItem
                    item.index = i+1


    def filter(self, attr):
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
        self.filter('trans')

    def require_gloss_lines(self):
        self.filter('gloss')

    def require_lang_lines(self):
        self.filter('lang')

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



    def giza_align_t_g(self, resume = True):
        """
        Perform giza alignments on the gloss and translation
        lines.

        :param resume: Whether to "resume" from the saved aligner, or start fresh.
        :type resume: bool
        """

        # Make sure that there are no spaces within a token, this will get us
        # all out of alignment...

        g_sents = []
        t_sents = []

        for inst in self:
            g_sent = []
            t_sent = []

            for gloss in inst.glosses.tokens():
                g_sent.append(re.sub('\s+','', gloss.value().lower()))
            g_sents.append(' '.join(g_sent))

            for trans in inst.trans.tokens():
                t_sent.append(re.sub('\s+', '', trans.value().lower()))
            t_sents.append(' '.join(t_sent))


        PARSELOG.info('Attempting to align instance "{}" with giza'.format(inst.id))

        if resume:
            # Next, load up the saved gloss-trans giza alignment model
            ga = GizaAligner.load(c['g_t_prefix'], c['g_path'], c['t_path'])

            # ...and use it to align the gloss line to the translation line.
            g_t_asents = ga.force_align(g_sents, t_sents)

        # Otherwise, start a fresh alignment model.
        else:
            ga = GizaAligner()
            g_t_asents = ga.temp_train(g_sents, t_sents)

        # Before continuing, make sure that we have the same number of alignments as we do instances.
        assert len(g_t_asents) == len(self), 'giza: %s -- self: %s' % (len(g_t_asents), len(self))

        # Next, iterate through the aligned sentences and assign their alignments
        # to the instance.
        for g_t_asent, igt in zip(g_t_asents, self):
            t_g_aln = g_t_asent.aln.flip()
            igt.set_bilingual_alignment(igt.trans, igt.glosses, t_g_aln, aln_method = INTENT_ALN_GIZA)

    def giza_align_l_t(self):
        """
        Perform giza alignments directly from language to translation lines, for comparison

        :rtype: Alignment
        """

        l_sents = [i.lang.text().lower() for i in self]
        t_sents = [i.trans.text().lower() for i in self]

        ga = GizaAligner()

        l_t_asents = ga.temp_train(l_sents, t_sents)

        assert len(l_t_asents) == len(self)

        for l_t_asent, igt in zip(l_t_asents, self):
            t_l_aln = l_t_asent.aln.flip()
            igt.set_bilingual_alignment(igt.trans, igt.lang, t_l_aln, aln_method = INTENT_ALN_GIZA)



    def heur_align(self, error=False):
        """
        Perform heuristic alignment between the gloss and translation.
        """
        for igt in self:
            try:
                PARSELOG.info('Attempting to heuristically align instance "{}"'.format(igt.id))
                g_heur_aln = igt.heur_align()
            except NoTransLineException as ntle:
                logging.warning(ntle)
                if error:
                    raise ntle
            except (NoGlossLineException, NoTransLineException, NoLangLineException) as ngle:
                logging.warning(ngle)
                if error:
                    raise ngle
            except MultipleNormLineException as mnle:
                logging.warning(mnle)
                if error:
                    raise mnle




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

    @classmethod
    def fromString(cls, string, corpus = None, require_1_to_1 = True, idnum=None):
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
            rt.add(l)

        inst.append(rt)

        # --- 4) Do the enriching if necessary

        inst.basic_processing(require_1_to_1 = require_1_to_1)
        # TODO: Clean up this exception handling
        try:
            inst.add_gloss_lang_alignments()
        except XigtFormatException as ngle:
            PARSELOG.warning(ngle)


        return inst

    def copy(self, parent = None):
        """
        Perform a custom deepcopy of ourselves.
        """
        new_i = RGIgt(id = self.id, type=self.type,
                    attributes = copy.deepcopy(self.attributes),
                    metadata = copy.copy(self.metadata),
                    corpus=parent)

        for tier in self.tiers:
            new_i.append(tier.copy(parent=new_i))

        return new_i


    def sort(self):
        """
        Sort an instance's tiers.
        """
        self._list = sorted(self._list, key=tier_sorter)



    # • Processing of newly created instances ----------------------------------

    def basic_processing(self, require_1_to_1 = True):
        # Create the clean tier
        """
        Finish the loading actions of an IGT instance. (Create the normal and
        clean tiers if they don't exist...)

        :param require_1_to_1:
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

    def add_gloss_lang_alignments(self):
        # Finally, do morpheme-to-morpheme alignment between gloss
        # and language if it's not already done...
        if not self.glosses.alignment:
            morph_align(self.glosses, self.morphemes)

        if not self.gloss.alignment:
            word_align(self.gloss, self.lang)



    # • Basic Tier Creation ------------------------------------------------------------

    def raw_tier(self):
        """
        Retrieve the raw ODIN tier, otherwise raise an exception.
        """
        raw_tier = self.find(type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE})

        if not raw_tier:
            raise NoODINRawException('No raw tier found.')
        else:
            return raw_tier

    def clean_tier(self):
        """
        If the clean odin tier exists, return it. Otherwise, create it.

        """

        # If a clean tier already exists, return it.
        clean_tier = self.find(type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:CLEAN_STATE})
        if clean_tier:
            return clean_tier

        else:
            # Otherwise, we will make our own:
            raw_tier = self.raw_tier()


            # Initialize the clean tier...
            clean_tier = RGLineTier(id = CLEAN_ID, type=ODIN_TYPE,
                         attributes={STATE_ATTRIBUTE:CLEAN_STATE,
                                    ALIGNMENT:raw_tier.id})

            # Gather the different tags used in this tier.
            # Note that we don't want to discard non-L,G,T tiers yet.
            line_tags = DefaultOrderedDict(list)
            for l in raw_tier:
                tags = l.attributes['tag'].split('+')
                primary = tags[0]
                others = tags[1:]
                line_tags[primary].append(l)

            # Now, the line_tags should be indexed by the primary
            # tag (L, G, T, etc...) with the +'s after it...


            # Now, go through and merge if needed.
            for primary_tag in line_tags.keys():

                lines = line_tags[primary_tag]

                if len(lines) == 1:
                    text = lines[0].value()
                    new_tag = lines[0].attributes['tag']
                    align_id = lines[0].id

                elif len(lines) > 1:
                    PARSELOG.info('Corruption detected in instance %s: %s' % (self.id, [l.attributes['tag'] for l in lines]))
                    for l in lines:
                        PARSELOG.debug('BEFORE: %s' % l)
                    text = merge_lines([l.value() for l in lines])
                    PARSELOG.debug('AFTER: %s' % text)
                    new_tag = primary_tag
                    align_id = ','.join([l.id for l in lines])

                item = RGLine(id=clean_tier.askItemId(), alignment=align_id, text=text,
                              attributes={'tag': new_tag})
                clean_tier.add(item)

            self.append(clean_tier)
            return clean_tier


    # • Word Tier Creation -----------------------------------

    def add_normal_line(self, tier, tag, func):
        clean_tier = self.clean_tier()
        clean_lines = [l for l in clean_tier if tag in l.attributes['tag'].split('+')]

        if len(clean_lines) > 1:
            PARSELOG.warning(rgencode(clean_tier))
            raise XigtFormatException("Clean tier should not have multiple lines of same tag.")

        # If there are clean lines for this tag... There must be only 1...
        # create it and add it to the tier.
        if clean_lines:
            item = RGLine(id=tier.askItemId(),
                        text=func(clean_lines[0].value()),
                        alignment=clean_lines[0].id,
                        attributes={'tag':tag})

            tier.add(item)

    def normal_tier(self):

            # If a normal tier already exists, return it.
            normal_tier = self.find(type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:NORM_STATE})
            if normal_tier:
                normal_tier.__class__ = RGTier
                return normal_tier

            # Otherwise, create a new one, with only L, G and T lines.
            else:
                normal_tier = RGLineTier(id = NORM_ID, type=ODIN_TYPE,
                                         attributes={STATE_ATTRIBUTE:NORM_STATE, ALIGNMENT:self.clean_tier().id})


                # Get one item per...
                self.add_normal_line(normal_tier, ODIN_LANG_TAG, clean_lang_string)
                self.add_normal_line(normal_tier, ODIN_GLOSS_TAG, clean_gloss_string)
                self.add_normal_line(normal_tier, ODIN_TRANS_TAG, clean_trans_string)

                self.append(normal_tier)
                return normal_tier





    # • Words Tiers ------------------------------------------------------------

    @property
    def lang(self):
        try:
            lt = retrieve_lang_words(self)
        except:
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
        # Make sure that we don't pick up the gloss-word tier by accident.
        f = [lambda x: not is_word_level_gloss(x)]

        gt = self.find(type=GLOSS_MORPH_TYPE, others=f)
        if gt:
            gt.__class__ = RGMorphTier

        # If we don't already have a sub-token-level glosses tier, let's create
        # it. Remembering that we want to use CONTENT to align the tier, not
        # SEGMENTATION.
        else:
            gt = self.gloss.morph_tier(GLOSS_MORPH_TYPE, GLOSS_MORPH_ID, CONTENT)

            # Add the meta information that this is not a word-level gloss.
            add_word_level_info(gt, INTENT_GLOSS_MORPH)

            self.append(gt)

        # If we have alignment, remove the metadata attribute.
        if gt.alignment is not None:
            remove_word_level_info(gt)

        return gt
    @property
    def morphemes(self):
        morphemes = self.find(type=LANG_MORPH_TYPE)
        if morphemes:
            morphemes.__class__ = RGMorphTier
            return morphemes
        else:
            mt = self.lang.morph_tier(LANG_MORPH_TYPE, LANG_MORPH_ID, SEGMENTATION)
            self.append(mt)
            return mt



    # • Alignment --------------------------------------------------------------

    def get_trans_gloss_alignment(self, aln_method=None):
        """
        Get the alignment between trans words and gloss words.
        """
        # If we already have this alignment, just return it.
        trans_gloss = self.get_bilingual_alignment(self.trans.id, self.gloss.id, aln_method)
        if trans_gloss:
            return trans_gloss

        # Otherwise, let's create it from the glosses alignment
        else:
            trans_glosses = self.get_bilingual_alignment(self.trans.id, self.glosses.id, aln_method)

            if not trans_glosses:
                raise ProjectionTransGlossException("Trans-to-gloss alignment must already exist, otherwise create with giza or heur")

            new_trans_gloss = Alignment()

            for trans_i, gloss_i in trans_glosses:
                gloss_m = self.glosses[gloss_i-1]
                gloss_w = find_gloss_word(self, gloss_m)

                new_trans_gloss.add((trans_i, gloss_w.index))

            return new_trans_gloss

    def get_trans_glosses_alignment(self, aln_method=None):
        """
        Convenience method for getting the trans-word to gloss-morpheme
        bilingual alignment.
        """
        return self.get_bilingual_alignment(self.trans.id, self.glosses.id, aln_method=aln_method)


    def get_gloss_lang_alignment(self):
        """
        Convenience method for getting the gloss-word to lang-word
        token based alignment
        """
        return self.gloss.get_aligned_tokens()

    def get_trans_gloss_lang_alignment(self):
        """
        Get the translation to lang alignment, travelling through the gloss line.
        """

        tg_aln = self.get_trans_gloss_alignment()
        gl_aln = self.get_gloss_lang_alignment()

        # Combine the two alignments...
        a = Alignment()
        for t_i, g_i in tg_aln:
            l_js = [l_j for (g_j, l_j) in gl_aln if g_j == g_i]
            for l_j in l_js:
                a.add((t_i, l_j))
        return a




    #===========================================================================
    # ALIGNMENT STUFF
    #===========================================================================

    def get_bilingual_alignment_tier(self, src_id, tgt_id, aln_method=None):
        """

        :param src_id:
        :type src_id: str
        :param tgt_id:
        :type tgt_id: str
        :param aln_method: Specify an alignment method that the alignment must be produced by.
        :rtype: RGTier
        """
        # Look for a previously created alignment of the same type.
        attributes = {SOURCE_ATTRIBUTE:src_id, TARGET_ATTRIBUTE:tgt_id}

        # Also add some search filters to match the metadata information, so that
        # we don't overwrite alignments provided by other sources.
        filters = []
        if aln_method:
            filters = [lambda x: get_intent_method(x) == aln_method]

        ba_tier = self.find(attributes=attributes, others=filters)
        return ba_tier


    def get_bilingual_alignment(self, src_id, tgt_id, aln_method=None):
        """
        Retrieve the bilingual alignment (assuming that the source tier is
        the translation words and that the target tier is the gloss morphemes.)
        :rtype : Alignment
        """

        ba_tier = self.get_bilingual_alignment_tier(src_id, tgt_id, aln_method)
        if not ba_tier:
            return None
        else:
            ba_tier.__class__ = RGBilingualAlignmentTier

            a = Alignment()
            # Now, iterate through the alignment tier
            for ba in ba_tier:
                ba.__class__ = RGBilingualAlignment
                src_item = self.find(id=ba.source)

                if not src_item:
                    PARSELOG.warn('Instance had src ID "%s", but no such ID was found.' % src_item)
                elif ba.target:
                    # There may be multiple targets, so get all the ids
                    # and find them...
                    tgt_ids = ref.ids(ba.target)
                    for tgt in tgt_ids:
                        tgt_item = self.find(id=tgt)

                        if tgt_item:
                            a.add((src_item.index, tgt_item.index))
                        else:
                            PARSELOG.warn('Instance had target ID "%s", but no such ID was found.' % tgt_item)

            return a

    def set_bilingual_alignment(self, src_tier, tgt_tier, aln, aln_method):
        """
        Specify the source tier and target tier, and create a bilingual alignment tier
        between the two, using the indices specified by the Alignment aln.

        :param src_tier: The tier that will be the source for bilingual alignments.
        :type src_tier: RGTier
        :param tgt_tier: The tier that will be the target for bilingual alignments.
        :type tgt_tier: RGTier
        :param aln: The alignment to be added
        :type aln: Alignment
        """

        # Look for any alignments previously generated by this method, and delete them
        # if found. Do NOT replace other alignments generated by other methods.
        prev_ba_tier = self.get_bilingual_alignment_tier(src_tier.id, tgt_tier.id, aln_method)
        if prev_ba_tier:
            prev_ba_tier.delete()

        # Just to make things neater, let's sort the alignment by src index.
        aln = sorted(aln, key = lambda x: x[0])

        # Start by creating the alignment tier.
        ba_tier = RGBilingualAlignmentTier(id=gen_tier_id(self, G_T_ALN_ID, tier_type=ALN_TIER_TYPE),
                                           source=src_tier.id, target=tgt_tier.id)

        # Add the metadata for the alignment source (intent) and type (giza or heur)
        set_intent_method(ba_tier, aln_method)

        for src_i, tgt_i in aln:
            src_token = src_tier[src_i-1]
            tgt_token = tgt_tier[tgt_i-1]

            ba_tier.add_pair(src_token.id, tgt_token.id)

        self.append(ba_tier)

    def heur_align(self, **kwargs):
        """
        Heuristically align the gloss and translation lines of this instance.
        """

        # If given the "tokenize" option, use the tokens
        # split at the morpheme level

        if kwargs.get('tokenize', True):
            gloss_tokens = self.glosses.tokens()
        else:
            gloss_tokens = self.gloss.tokens()

        trans_tokens = self.trans.tokens()

        aln = heur_alignments(gloss_tokens, trans_tokens, **kwargs).flip()

        # Now, add these alignments as bilingual alignments...
        self.set_bilingual_alignment(self.trans, self.glosses, aln, aln_method=INTENT_ALN_HEUR)



    # • POS Tag Manipulation ---------------------------------------------------------------

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

    def get_pos_tags(self, tier_id, tag_method = None):
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

        pos_tier = self.find(attributes={ALIGNMENT:tier_id}, type=POS_TIER_TYPE, others = filters)

        # If we found a tier, return it with the token methods...
        if pos_tier is not None:
            pos_tier.__class__ = RGTokenTier
            return pos_tier

        # Otherwise, return None...


    def get_lang_sequence(self, created_by = None, unk_handling=None):
        """
        Retrieve the language line, with as many POS tags as are available.
        """
        # TODO: This is another function that needs reworking
        w_tags = self.get_pos_tags(self.lang.id, created_by)

        if not w_tags:
            project_creator_except("Language-line POS tags were not found", "To obtain the language line sequence, please project or annotate the language line.", created_by)

        seq = []

        for w in self.lang:
            w_tag = w_tags.find(attributes={ALIGNMENT:w.id})
            if not w_tag:
                if unk_handling == None:
                    w_tag = 'UNK'
                elif unk_handling == 'noun':
                    w_tag = 'NOUN'
                else:
                    raise ProjectionException('Unknown unk_handling attribute')

            w_content = w.value().lower()
            w_content = surrounding_quotes_and_parens(remove_hyphens(w_content))

            w_content = re.sub(punc_re, '', w_content)


            seq.append(POSToken(w_content, label=w_tag))
        return seq

    # • POS Tag Production -----------------------------------------------------

    def tag_trans_pos(self, tagger):
        """
        Run the stanford tagger on the translation words and return the POS tags.

        :param tagger: The active POS tagger model.
        :type tagger: StanfordPOSTagger
        """

        trans_tags = [i.label for i in tagger.tag(self.trans.text())]

        # Add the generated pos tags to the tier.
        self.add_pos_tags(self.trans.id, trans_tags, tag_method=INTENT_POS_TAGGER)
        return trans_tags

    def classify_gloss_pos(self, classifier, tag_method=None, **kwargs):
        """
        Run the classifier on the gloss words and return the POS tags.

        :param classifier: the active mallet classifier to classify this language line.
        :type classifier: MalletMaxent
        """

        attributes = {ALIGNMENT:self.gloss.id}

        # Search for a previous run and remove if found...
        prev_tier = self.get_pos_tags(self.gloss.id, tag_method = tag_method)

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
                result = classifier.classify_string(gloss_token, **kwargs)

                best = result.largest()

                # Return the POS tags
                tags.append(best[0])

        self.add_pos_tags(self.gloss.id, tags, tag_method=INTENT_POS_CLASS)
        return tags

    # • POS Tag Projection -----------------------------------------------------
    def project_trans_to_gloss(self, tag_method=None):
        """
        Project POS tags from the translation words to the gloss words.
        """

        # Remove previous gloss tags created by us if specified...
        attributes = {ALIGNMENT:self.gloss.id}

        # Remove the previous tags if they are present...
        prev_t = self.get_pos_tags(self.gloss.id, tag_method=tag_method)
        if prev_t: prev_t.delete()

        # Get the trans tags...
        trans_tags = self.get_pos_tags(self.trans.id)

        # If we don't get any trans tags back, throw an exception:
        if not trans_tags:
            project_creator_except("There were no translation-line POS tags found",
                                   "Please create the appropriate translation-line POS tags before projecting.",
                                   tag_method)

        t_g_aln = sorted(self.get_trans_gloss_alignment())

        # Create the new pos tier.
        # TODO: There should be a more unified approach to transferring tags.

        pt = RGTokenTier(type=POS_TIER_TYPE,
                         id=gen_tier_id(self, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=self.gloss.id),
                         alignment=self.gloss.id, attributes=attributes)

        # Add the metadata about this tier...
        set_intent_method(pt, INTENT_POS_PROJ)
        set_intent_proj_data(pt, trans_tags)


        for t_i, g_i in t_g_aln:
            g_word = self.gloss.get_index(g_i)
            t_tag = trans_tags[t_i-1]

            # TODO: Implement order of precedence here.

            pt.add(RGToken(id=pt.askItemId(), alignment=g_word.id, text=t_tag.value()))

        self.append(pt)

    def project_gloss_to_lang(self, tag_method = None, unk_handling=None, classifier=None, posdict=None):
        """
        Project POS tags from gloss words to language words. This assumes that we have
        alignment tags on the gloss words already that align them to the language words.
        """

        gloss_tags = self.get_pos_tags(self.gloss.id, tag_method=tag_method)

        # If we don't have gloss tags by that creator...
        if not gloss_tags:
            project_creator_except("There were no gloss-line POS tags found",
                                    "Please create the appropriate gloss-line POS tags before projecting.",
                                    tag_method)

        alignment = self.gloss.get_aligned_tokens()

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
        set_intent_proj_data(pt, gloss_tags)

        for g_idx, l_idx in alignment:
            l_w = self.lang.get_index(l_idx)
            g_w = self.gloss.get_index(g_idx)

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
        set_intent_proj_data(pt, trans_tags)

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

        trans = self.trans.text().replace('(', '[')
        trans = trans.replace(')',']')

        result = parser.parse(trans)

        PARSELOG.debug('Result of translation parse: {}'.format(result.pt))

        if pt:
            self.create_pt_tier(result.pt, self.trans, parse_method=INTENT_PS_PARSER)
        if dt:
            self.create_dt_tier(result.dt, parse_method=INTENT_DS_PARSER)


    def create_pt_tier(self, phrase_tree, w_tier, parse_method=None, source_tier=None):
        """
        Given a phrase tree, create a phrase tree tier. The :class:`intent.trees.IdTree` passed in must
        have the same number of leaves as words in the translation line.

        :param phrase_tree: Phrase tree.
        :type phrase_tree: IdTree
        :param w_tier: Word tier
        :type w_tier: RGWordTier
        :param source_tier: If this tier is being projected, add that fact to the metadata.
        """

        # 1) Start by creating a phrase structure tier -------------------------
        pt_id = gen_tier_id(self, PS_TIER_ID, tier_type=PS_TIER_TYPE, alignment=w_tier.id)
        pt_tier = RGPhraseStructureTier(type=PS_TIER_TYPE,
                                        id=pt_id,
                                        alignment=w_tier.id,
                                        attributes={PS_CHILD_ATTRIBUTE:pt_id})

        # 2) Add the intent metadata...
        set_intent_method(pt_tier, parse_method)
        if source_tier is not None:
            set_intent_proj_data(pt_tier, source_tier)

        phrase_tree.assign_ids(pt_tier.id)

        # We should get back the same number of tokens as we put in
        assert len(phrase_tree.leaves()) == len(w_tier)

        leaves = list(phrase_tree.leaves())
        preterms = list(phrase_tree.preterminals())

        assert len(leaves) == len(preterms)

        # 2) Now, run through the leaves and the preterminals ------------------
        for wi, preterm in zip(w_tier, preterms):

            # Note that the preterminals align with a given word...
            pi = RGItem(id=preterm.id, alignment=wi.id, text=preterm.label())
            pt_tier.add(pi)

        # 3) Finally, run through the rest of the subtrees. --------------------
        for st in phrase_tree.nonterminals():
            child_refs = ' '.join([s.id for s in st])
            si = RGItem(id=st.id, attributes={PS_CHILD_ATTRIBUTE:child_refs}, text=st.label())
            pt_tier.add(si)

        # 4) And add the created tier to this instance. ------------------------
        self.append(pt_tier)

    def get_trans_parse_tier(self):
        """
        Get the phrase structure tier aligned with the translation words.
        """
        return self.find(type=PS_TIER_TYPE, attributes={ALIGNMENT:self.trans.id})

    def project_pt(self):

        """

        :raise PhraseStructureProjectionException: If there is no translation parse already in the tree, raise this error.
        """
        trans_parse_tier = self.get_trans_parse_tier()

        if trans_parse_tier is None:
            raise PhraseStructureProjectionException('Translation parse not found for instance "%s"' % self.id)

        trans_tree = read_pt(trans_parse_tier)

        # This might raise a ProjectionTransGlossException if the trans and gloss
        # alignments don't exist.
        tl_aln = self.get_trans_gloss_lang_alignment()

        # Do the actual tree projection and create a tree object
        proj_tree = project_ps(trans_tree, self.lang, tl_aln)

        # Now, create a tier from that tree object.
        self.create_pt_tier(proj_tree, self.lang, parse_method=INTENT_PS_PROJ, source_tier=self.get_trans_parse_tier())


    def create_dt_tier(self, dt, parse_method=None):
        """
        Create the dependency structure tier based on the ds that is passed in. The :class:`intent.trees.DepTree`
        structure that is passed in must be based on the words in the translation line, as the indices from the
        dependency tree will be used to identify the tokens.

        :param dt: Dependency tree to create a tier for.
        :type dt: DepTree
        """

        # 1) Start by creating dt tier -----------------------------------------
        dt_tier = RGTier(type=DS_TIER_TYPE,
                         id=gen_tier_id(self, DS_TIER_ID, DS_TIER_TYPE, alignment=self.trans.id),
                         attributes={DS_DEP_ATTRIBUTE: self.trans.id, DS_HEAD_ATTRIBUTE: self.trans.id})

        set_intent_method(dt_tier, parse_method)

        # 2) Next, simply iterate through the tree and make the head/dep mappings.

        for label, head_i, dep_i in dt.indices_labels():

            attributes={DS_DEP_ATTRIBUTE:self.trans.get_index(dep_i).id}

            if head_i != 0:
                attributes[DS_HEAD_ATTRIBUTE] = self.trans.get_index(head_i).id


            di = RGItem(id=dt_tier.askItemId(), attributes=attributes, text=label)
            dt_tier.add(di)

        self.append(dt_tier)







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
        self.index = kwargs.get('index')

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

    def __init__(self, index=None, **kwargs):
        RGItem.__init__(self, **kwargs)
        self.index = index


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

    def get_index(self, index):
        """
        Get the item at the given index, indexed from 1

        :param index: index of the element (starting from 1)
        :type index: int
        """
        return self.items[index-1]

    def askItemId(self):
        return gen_item_id(self.id, len(self))

    def askIndex(self):
        return len(self.items)+1

    def text(self, remove_whitespace_inside_tokens = True):
        """
        Return a whitespace-delimeted string consisting of the
        elements of this tier. Default to removing whitespace
        that occurs within a token.
        """
        tokens = [str(i) for i in self.tokens()]
        if remove_whitespace_inside_tokens:

            # TODO: Another whitespace replacement handling
            tokens = [re.sub('\s+','',i) for i in tokens]

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
        del self.igt.tiers[self.index]
        self.igt.refresh_index()

#===============================================================================
# Bilingual Alignment Tier
#===============================================================================
class RGBilingualAlignmentTier(RGTier):
    """
    Special tier type for handling bilingual alignments.
    """
    def __init__(self, source=None, target=None, **kwargs):
        super().__init__(type=ALN_TIER_TYPE, **kwargs)

        if source:
            self.attributes[SOURCE_ATTRIBUTE] = source

        if target:
            self.attributes[TARGET_ATTRIBUTE] = target



    def add_pair(self, src, tgt):
        """
        Add a (src,tgt) pair of ids to the tier if they are not already there,
        otherwise add the tgt on to the src. (We are operating on the paradigm
        here that the source can specify multiple target ids, but only one srcid
        per item).
        """
        i = self.find(attributes={SOURCE_ATTRIBUTE:src, TARGET_ATTRIBUTE:tgt})

        # If the source is not found, add
        # a new item.
        if not i:
             ba = RGBilingualAlignment(id=self.askItemId(), source=src, target=tgt)
             self.add(ba)

        # If the source is already here, add the target to its
        # target refs.
        else:
            i.attributes[TARGET_ATTRIBUTE] += ',' + tgt




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
    tpt = retrieve_phrase(inst, ODIN_TRANS_TAG, TRANS_PHRASE_ID, TRANS_PHRASE_TYPE)

    # Add the alignment with the language line phrase if it's not already there.
    if ALIGNMENT not in tpt.attributes:
        lpt = retrieve_lang_phrase(inst)
        tpt.attributes[ALIGNMENT] = lpt.id
        tpt[0].attributes[ALIGNMENT] = lpt[0].id

    return tpt

def retrieve_lang_phrase(inst):
    """
    Retrieve the language phrase if it exists, otherwise create it.

    :param inst: Instance to search
    :type inst: RGIgt
    """
    return retrieve_phrase(inst, ODIN_LANG_TAG, LANG_PHRASE_ID, LANG_PHRASE_TYPE)

def retrieve_phrase(inst, tag, id, type):
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

    n = inst.normal_tier()

    pt = inst.find(type=type, content = n.id)
    if not pt:
        # Get the normalized line line
        l = retrieve_normal_line(inst, tag)
        pt = RGPhraseTier(id=id, type=type, content=n.id)
        pt.add(RGPhrase(id=pt.askItemId(), content=l.id))
        inst.append(pt)
    else:
        pt.__class__ = RGPhraseTier

    return pt

#===============================================================================
# • Word Tier Creation ---
#===============================================================================

def create_words_tier(cur_item, word_id, word_type, aln_attribute = SEGMENTATION):
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


    # Tokenize the words in this phrase...
    words = intent.utils.token.tokenize_item(cur_item)

    # Create a new word tier to hold the tokenized words...
    wt = RGWordTier(id = word_id, type=word_type, attributes={aln_attribute:cur_item.tier.id}, igt=cur_item.igt)

    for w in words:
        # Create a new word that is a segmentation of this tier.
        rw = RGWord(id=wt.askItemId(), attributes={aln_attribute:create_aln_expr(cur_item.id, w.start, w.stop)}, tier=wt, start=w.start, stop=w.stop)
        wt.add(rw)

    return wt

def retrieve_trans_words(inst):
    """
    Retrieve the translation words tier from an instance.

    :type inst: RGIgt
    :rtype: RGWordTier
    """

    # Get the translation phrase tier
    tpt = retrieve_trans_phrase(inst)

    # Get the translation word tier
    twt = inst.find(
                type=TRANS_WORD_TYPE,
                segmentation=tpt.id)

    if not twt:
        twt = create_words_tier(tpt[0], TRANS_WORD_ID, TRANS_WORD_TYPE)
        inst.append(twt)
    else:
        twt.__class__ = RGWordTier

    return twt

def retrieve_lang_words(inst):
    """
    Retrieve the language words tier from an instance

    :type inst: RGIgt
    :rtype: RGWordTier
    """
    # Get the lang phrase tier
    lpt = retrieve_lang_phrase(inst)

    # Get the lang word tier
    lwt = inst.find(type=LANG_WORD_TYPE, segmentation=lpt.id)

    if not lwt:
        lwt = create_words_tier(lpt[0], LANG_WORD_ID, LANG_WORD_TYPE)
        inst.append(lwt)
    else:
        lwt.__class__ = RGWordTier

    return lwt


def retrieve_gloss_words(inst):
    """
    Given an IGT instance, create the gloss "words" and "glosses" tiers.

    1. If a "words" type exists, and it's contents are the gloss line, return it.
    2. If it does not exist, tokenize the gloss line and return it.

    :param inst: Instance which to create the tiers from.
    :type inst: RGIgt
    :rtype: RGWordTier
    """

    # 1. Look for an existing words tier that aligns with the normalized tier...
    n = inst.normal_tier()
    wt = inst.find(type=GLOSS_WORD_TYPE, content=n.id,
                   # Add the "others" to find only the "glosses" tiers that
                   # are at the word level...
                   others=[lambda x: is_word_level_gloss(x)])

    # 2. If it exists, return it. Otherwise, look for the glosses tier.
    if not wt:
        wt = create_words_tier(retrieve_normal_line(inst, ODIN_GLOSS_TAG), GLOSS_WORD_ID,
                               GLOSS_WORD_TYPE, aln_attribute=CONTENT)

        # Set the "gloss type" to the "word-level"
        add_word_level_info(wt, INTENT_GLOSS_WORD)
        inst.append(wt)
    else:
        wt.__class__ = RGWordTier


    # If we have alignment, we can remove the metadata, because
    # that indicates the type for us.
    if wt.alignment is not None:
        remove_word_level_info(wt)

    return wt

def retrieve_normal_line(inst, tag):
    """
    Retrieve a normalized line from the instance ``inst`` with the given ``tag``.

    :param inst: Instance to retrieve the normalized line from.
    :type inst: RGIgt
    :param tag: {'L', 'G', or 'T'}
    :type tag: str

    :rtype: RGPhrase
    """

    n = inst.normal_tier()

    lines = [l for l in n if tag in l.attributes['tag'].split('+')]

    if len(lines) < 1:
        raise NoNormLineException()
    elif len(lines) > 1:
        raise MultipleNormLineException('Multiple normalized lines found for tag "{}" in instance {}'.format(tag, inst.id))
    else:
        return lines[0]



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

    if len(gloss_tier) != len(morph_tier):
        raise GlossLangAlignException("Gloss tier of length {} cannot automatically align to morph tier of length {}".format(len(gloss_tier), len(morph_tier)))

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
    for gloss in gloss_tier:

        gloss_word = find_gloss_word(gloss_tier.igt, gloss)
        word_id = gloss_word.alignment

        # Next, let's see what unaligned morphs there are
        aligned_lang_morphs = lang_word_dict[word_id]

        # If there's only one morph left, align with that.
        if len(aligned_lang_morphs) == 1:
            gloss.alignment = aligned_lang_morphs[0].id

        # If there's more, pop one off the beginning of the list and use that.
        # This will cause subsequent morphs to align to the rightmost morph
        # that also aligns to the same word
        elif len(aligned_lang_morphs) > 1:
            lang_morph = aligned_lang_morphs.pop(0)
            gloss.alignment = lang_morph.id

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


def odin_span(inst, item):
    """
    Follow this item's segmentation all the way
    back to the raw odin item it originates from.

    :param inst: Instance to pull from
    :type inst: RGIgt
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

        for aligned_object, span in resolve_objects(inst, aln_expr):
            if span is None:
                spans.extend(odin_span(inst, aligned_object))
            else:
                aln_start, aln_stop = span
                for start, stop in odin_span(inst, aligned_object):
                    spans.extend([(start+aln_start, start+aln_stop)])

        return spans





def x_contains_y(inst, x_item, y_item):
    return x_span_contains_y(odin_span(inst, x_item), odin_span(inst, y_item))

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

    for g in inst.gloss:

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
    add_meta(obj, INTENT_EXTENDED_INFO, INTENT_TOKEN_TYPE, val, metadata_type=INTENT_META_TYPE)

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
    # If we have explicit metadata that says we are a word,
    # return true.
    if get_word_level_info(obj) == INTENT_GLOSS_WORD:
        return True

    # Otherwise, check and see if we are aligned with a
    elif isinstance(obj, Tier):
        a = obj.igt.find(id=obj.alignment)
        return (a is not None) and (a.type == WORDS_TYPE)


#===============================================================================
# • Sorting ---
#===============================================================================

def sort_idx(l, v):
    """
    Return the index of an item in a list, otherwise the length of the list (for sorting)

    :param l: list
    :param v: value
    """
    try:
        return l.index(v)
    except:
        return len(l)

def tier_sorter(x):
    """
    ``key=`` function to sort a tier according to tier type,
    tier state (for ODIN tiers), and word_id (for word
    tiers that all share the same type attribute)
    """
    type_order = [ODIN_TYPE,
                    LANG_PHRASE_TYPE, TRANS_PHRASE_TYPE,
                    LANG_WORD_TYPE, GLOSS_WORD_TYPE, TRANS_WORD_TYPE,
                    LANG_MORPH_TYPE, GLOSS_MORPH_TYPE,
                    POS_TIER_TYPE, ALN_TIER_TYPE, PS_TIER_TYPE, DS_TIER_TYPE, None]

    state_order = [RAW_STATE, CLEAN_STATE, NORM_STATE]
    word_id_order = [LANG_WORD_ID, GLOSS_WORD_ID, TRANS_WORD_ID]


    state_index = sort_idx(state_order, x.attributes.get('state'))
    type_index = sort_idx(type_order, x.type)
    id_index = sort_idx(word_id_order, x.id)

    return (type_index, state_index, id_index, x.id)

#===============================================================================
# • Cleaning ---
#===============================================================================


def strip_enrichment(inst):
    strip_pos(inst)
    for at in inst.findall(type='bilingual-alignments'):
        at.delete()

def strip_pos(inst):
    for pt in inst.findall(type='pos'):
        pt.delete()




from intent.trees import IdTree, project_ps, Terminal