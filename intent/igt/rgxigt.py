# coding=UTF-8
"""
Subclassing of the xigt package to add a few convenience methods.
"""

#===============================================================================
# Logging
#===============================================================================

import logging

# Set up logging ---------------------------------------------------------------
from intent.igt.create_tiers import trans_lines, get_raw_tier, generate_clean_tier, add_normal_line_to_tier, generate_normal_tier, morphemes
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




    # • Processing of newly created instances ----------------------------------




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


