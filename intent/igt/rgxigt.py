# coding=UTF-8
"""
Subclassing of the xigt package to add a few convenience methods.
"""

#===============================================================================
# Logging
#===============================================================================

import logging

# Set up logging ---------------------------------------------------------------
from intent.igt.create_tiers import trans_line, get_raw_tier, generate_clean_tier, add_normal_line_to_tier, generate_normal_tier, morphemes
from intent.utils.string_utils import replace_invalid_xml
from xigt.errors import XigtError

PARSELOG = logging.getLogger(__name__)
ALIGN_LOG = logging.getLogger('GIZA_LN')
ODIN_LOG = logging.getLogger('ODIN_LOOKUP')
CONVERT_LOG = logging.getLogger('CONVERSION')

# XIGT imports -----------------------------------------------------------------
from xigt.codecs import xigtxml
from xigt.model import XigtCorpus, Igt, Item

# INTERNAL imports -------------------------------------------------------------


from intent.alignment.Alignment import Alignment


# ===============================================================================


class RGCorpus(XigtCorpus):


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
        return xc


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



class RGIgt(Igt):

    # • Constructors -----------------------------------------------------------

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


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
            id = 'i{}'.format(len(corpus))

        inst = cls(id = id, attributes={'doc-id':docid,
                                            'line-range':'%s %s' % (lnstart, lnstop),
                                            'tag-types':tagtypes})

        # Now, find all the lines
        lines = re.findall('line=([0-9]+)\stag=(\S+):(.*)\n?', string)

        # --- 3) Create a raw tier.
        rt = Tier(id = RAW_ID, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE}, igt=inst)

        for lineno, linetag, linetxt in lines:
            l = RGLine(id = ask_item_id(rt), text=linetxt, attributes={'tag':linetag, 'line':lineno}, tier=rt)
            rt.append(l)

        inst.append(rt)

        # --- 4) Do the enriching if necessary

        inst.basic_processing()

        return inst


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
            trans(self)
        except XigtFormatException:
            pass

        try:
            gloss(self)
        except XigtFormatException:
            pass

        try:
            haslang = lang(self)
        except XigtFormatException:
            haslang = False

        # Create the morpheme tiers...
        try:
            hasgloss = glosses(self)
        except NoGlossLineException:
            hasgloss = False

        try:
            morphemes(self)
        except NoLangLineException:
            pass

        # And do word-to-word alignment if it's not already done.
        if hasgloss and haslang and not gloss(self).alignment:
            word_align(gloss(self), lang(self))

        if hasgloss and haslang:
            self.add_gloss_lang_alignments()


    def add_gloss_lang_alignments(self):
        # Finally, do morpheme-to-morpheme alignment between gloss
        # and language if it's not already done...
        if not glosses(self).alignment:
            morph_align(glosses(self), morphemes(self))

        if not gloss(self).alignment:
            word_align(gloss(self), lang(self))

    # • Basic Tier Creation ------------------------------------------------------------

    def raw_tier(self):
        return get_raw_tier(self)

    def clean_tier(self, merge=False, generate=True):
        return generate_clean_tier(self, merge, generate)


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
        return generate_normal_tier(self, clean, generate)



    #===========================================================================
    # ALIGNMENT STUFF
    #===========================================================================


    def heur_align(self, **kwargs):
        return heur_align_inst(self, **kwargs)

    # -------------------------------------------
    # POS TAG MANIPULATION
    # -------------------------------------------






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
        pt = Tier(type=POS_TIER_TYPE, id=pos_id, alignment=self.lang.id)

        # Add the metadata about the source of the tags.
        set_intent_method(pt, INTENT_POS_PROJ)
        set_intent_proj_data(pt, trans_tags, ta_aln.type)

        for t_i, l_i in ta_aln:
            t_word = self.trans.get_index(t_i)
            t_tag = trans_tags[t_i-1]

            l_word = self.lang.get_index(l_i)

            pt.add(RGToken(id=ask_item_id(pt), alignment = l_word.id, text = str(t_tag)))

        self.append(pt)



#===============================================================================
# Items
#===============================================================================

class RGItem(Item):
    """
    Subclass of the xigt core "Item."
    """

    def __init__(self, **kwargs):

        new_kwargs = {key : value for key, value in kwargs.items() if key not in ['index', 'start', 'stop']}

        super().__init__(**new_kwargs)

        self.start = kwargs.get('start')
        self.stop = kwargs.get('stop')


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





from .igt_functions import *