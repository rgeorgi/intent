from intent.igt.metadata import get_intent_method, get_word_level_info, add_word_level_info, remove_word_level_info
from intent.utils.dicts import DefaultOrderedDict
from xigt import Tier, Item
from xigt.consts import ALIGNMENT, SEGMENTATION, CONTENT

from .exceptions import *
from .references import xigt_find, gen_item_id, create_aln_expr, ask_item_id, odin_tags, raw_tier
from .igtutils import clean_trans_string, clean_gloss_string, clean_lang_string, strip_leading_whitespace, extract_judgment, \
    concat_lines
from intent.utils.token import sentence_tokenizer, tokenize_item, morpheme_tokenizer, whitespace_tokenizer
from intent.consts import *

import logging
TIER_LOG = logging.getLogger("TIER_CREATION")



# -------------------------------------------
# Create a words tier.
# -------------------------------------------
def create_words_tier(cur_item, word_id, word_type, aln_attribute = SEGMENTATION, tokenizer=sentence_tokenizer):
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
        words = tokenize_item(cur_item, tokenizer=tokenizer)

    # Create a new word tier to hold the tokenized words...
    wt = Tier(id = word_id, type=word_type, attributes={aln_attribute:cur_item.tier.id}, igt=cur_item.igt)

    for w in words:
        # Create a new word that is a segmentation of this tier.
        rw = Item(id=gen_item_id(wt.id, len(wt)),
                  attributes={aln_attribute:create_aln_expr(cur_item.id, w.start, w.stop)}, tier=wt)
        wt.append(rw)

    return wt

# -------------------------------------------
# Word tiers
# -------------------------------------------
def _word_tier(inst, r_func, ex):
    """
    :param r_func: The retrieval function
    :param ex:  The exception to throw
    """
    try:
        t = r_func(inst)
    except NoNormLineException:
        raise ex
    else:
        return t


def lang(inst) -> Tier:
    return _word_tier(inst, generate_lang_words, NoLangLineException)

def gloss(inst) -> Tier:
    return _word_tier(inst, generate_gloss_glosses, NoGlossLineException)

def trans(inst) -> Tier:
    return _word_tier(inst, generate_trans_words, NoTransLineException)

# =============================================================================
# WORD TIER GENERATION
# =============================================================================

def generate_lang_words(inst, create=True):
    """
    Retrieve the language words tier from an instance

    :type inst: RGIgt
    :rtype: RGWordTier
    """
    # Get the lang phrase tier
    lpt = generate_lang_phrase_tier(inst)

    # Get the lang word tier
    lwt = xigt_find(inst, type=LANG_WORD_TYPE, segmentation=lpt.id)

    if lwt is None and create:
        lwt = create_words_tier(lpt[0], LANG_WORD_ID, LANG_WORD_TYPE)
        inst.append(lwt)

    return lwt

def generate_gloss_glosses(inst, create=True):
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
    gloss_tier = xigt_find(inst, type=GLOSS_WORD_TYPE,
                   # Add the "others" to find only the "glosses" tiers that
                   # are at the word level...

                           # TODO FIXME: Find more elegant solution
                           others=[lambda x: is_word_level_gloss(x),
                                   lambda x: ODIN_GLOSS_TAG in odin_tags(x)])

    # 2. If it exists, return it. Otherwise, look for the glosses tier.
    if gloss_tier is None:
        if create:
            n = generate_normal_tier(inst)
            gloss_line_item = retrieve_normal_lines(inst, ODIN_GLOSS_TAG)[0]

            # If the value of the gloss line is None, or it's simply an empty string...
            if gloss_line_item is None or gloss_line_item.value() is None or not gloss_line_item.value().strip():
                raise EmptyGlossException()
            else:
                gloss_tier = create_words_tier(gloss_line_item, GLOSS_WORD_ID,
                                               GLOSS_WORD_TYPE, aln_attribute=CONTENT,
                                               tokenizer=whitespace_tokenizer)

            # Set the "gloss type" to the "word-level"
            add_word_level_info(gloss_tier, INTENT_GLOSS_WORD)
            inst.append(gloss_tier)
            return gloss_tier

        else:
            return None

    else:
        # If we have alignment, we can remove the metadata, because
        # that indicates the type for us.
        if gloss_tier.alignment is not None:
            remove_word_level_info(gloss_tier)

        return gloss_tier


def generate_trans_words(inst, create=True):
    """
    Retrieve the translation words tier from an instance.

    :type inst: RGIgt
    :rtype: RGWordTier
    """

    # Get the translation phrase tier
    tpt = generate_trans_phrase_tier(inst)

    # Get the translation word tier
    twt = xigt_find(inst,
                    type=TRANS_WORD_TYPE,
                    segmentation=tpt.id)

    if twt is None and create:
        twt = create_words_tier(tpt[0], TRANS_WORD_ID, TRANS_WORD_TYPE, tokenizer=sentence_tokenizer)
        inst.append(twt)

    return twt

# -------------------------------------------
# Morpheme/Gloss Tiers
# -------------------------------------------

def morphemes(inst) -> Tier:
    mt = xigt_find(inst, type=LANG_MORPH_TYPE)
    if mt is None:
        mt = words_to_morph_tier(lang(inst), LANG_MORPH_TYPE, LANG_MORPH_ID, SEGMENTATION)
        inst.append(mt)
    return mt

def glosses(inst) -> Tier:
    # Make sure that we don't pick up the gloss-word tier by accident.
    f = [lambda x: not is_word_level_gloss(x)]

    gt = xigt_find(inst, type=GLOSS_MORPH_TYPE, others=f)


    # If we don't already have a sub-token-level glosses tier, let's create
    # it. Remembering that we want to use CONTENT to align the tier, not
    # SEGMENTATION.
    if gt is None:
        gt = words_to_morph_tier(gloss(inst), GLOSS_MORPH_TYPE, GLOSS_MORPH_ID, CONTENT)

        # Add the meta information that this is not a word-level gloss.
        add_word_level_info(gt, INTENT_GLOSS_MORPH)
        inst.append(gt)

    # If we have alignment, remove the metadata attribute.
    if gt.alignment is not None:
        remove_word_level_info(gt)

    return gt


# =============================================================================
# PHRASES
# =============================================================================

def generate_phrase_tier(inst, tag, id, type) -> Tier:
    """
    Retrieve a phrase for the given tag, with the provided id and type.
    """

    f = lambda x: tag in odin_tags(x)
    pt = xigt_find(inst, type=type, others=[f])


    if pt is None:
        normal_tier = generate_normal_tier(inst)

        # Create the phrase tier
        pt = Tier(id=id, type=type, content=normal_tier.id)

        for normal_line in retrieve_normal_lines(inst, tag):

            # -------------------------------------------
            # Propagate the judgment attribute on the line to the phrase item
            # -------------------------------------------
            phrase_attributes = {}
            old_judgment = normal_line.attributes.get(ODIN_JUDGMENT_ATTRIBUTE)
            if normal_line.attributes.get(ODIN_JUDGMENT_ATTRIBUTE) is not None:
                phrase_attributes[ODIN_JUDGMENT_ATTRIBUTE] = old_judgment

            # -------------------------------------------
            # Finally, create the phrase item, and
            # add it to the phrase tier.
            # -------------------------------------------
            pt.append(Item(id=ask_item_id(pt), content=normal_line.id, attributes=phrase_attributes))
            inst.append(pt)

    return pt

def generate_lang_phrase_tier(inst):
    """
    Retrieve the language phrase if it exists, otherwise create it.
    """
    return generate_phrase_tier(inst, ODIN_LANG_TAG, LANG_PHRASE_ID, LANG_PHRASE_TYPE)

def generate_trans_phrase_tier(inst):
    """
    Retrieve the translation phrase tier if it exists, otherwise create it. (Making
    sure to align it with the language phrase if it is present)
    """
    tpt = generate_phrase_tier(inst, ODIN_TRANS_TAG, TRANS_PHRASE_ID, TRANS_PHRASE_TYPE)

    # Add the alignment with the language line phrase if it's not already there.
    if ALIGNMENT not in tpt.attributes:
        try:
            lpt = generate_lang_phrase_tier(inst)
            tpt.attributes[ALIGNMENT] = lpt.id
            tpt[0].attributes[ALIGNMENT] = lpt[0].id
        except MultipleNormLineException as mnle:
            pass
        except NoNormLineException as nlle:
            pass

    return tpt

# =============================================================================
# ODIN LINES
# =============================================================================

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
        a = xigt_find(obj.igt, id=obj.alignment)
        return (a is not None) and (a.type == WORDS_TYPE)






# =============================================================================
# ODIN LINES
# =============================================================================

def sort_lines(l):
    tags = l.attributes[ODIN_TAG_ATTRIBUTE].split('+')
    return (l.attributes.get(ODIN_JUDGMENT_ATTRIBUTE, ''), tags)

def retrieve_normal_lines(inst, tag):
    """
    Get all the normalized lines .
    :rtype: list[Item]
    """
    norm_tier = generate_normal_tier(inst)
    lines = [line for line in norm_tier if tag in line.attributes[ODIN_TAG_ATTRIBUTE].split('+')]
    if not lines:
        raise NoNormLineException('No normalized lines were available for tag "{}" in instance "{}"'.format(tag, inst.id))
    return sorted(lines, key=sort_lines)


def lang_lines(inst):
    return retrieve_normal_lines(inst, ODIN_LANG_TAG)

def gloss_line(inst) -> Item:
    lines = retrieve_normal_lines(inst, ODIN_GLOSS_TAG)
    if lines:
        return lines[0]
    else:
        return None

def trans_lines(inst):
    return retrieve_normal_lines(inst, ODIN_TRANS_TAG)




# -------------------------------------------
#
# -------------------------------------------

def get_raw_tier(inst):
    """
    Retrieve the raw ODIN tier, otherwise raise an exception.
    """
    rt = raw_tier(inst)

    if not rt:
        raise NoODINRawException('No raw tier found.')
    else:
        return rt

# =============================================================================
# TIER GENERATION
# =============================================================================

def generate_normal_tier(inst, clean=True, generate=True, force_generate=False):
    """
    1) Find the normalized tier if it exists.
    2) Generate it from the cleaned tier if:
        a) The "force_generate" option is set to true
        b) It does not already exist

    3) Return 1 if it exists, or the result of 2, if it exists, otherwise None.

    :param inst: The instance to retrieve the normal tier from.
    :param clean: Whether to attempt to automatically clean the instance or not.
    :type clean: bool
    :param generate: Whether to generate the normalized line if it doesn't exist.
    :type generate: bool
    :param force_generate: If the normal line already exists, overwrite it?
    :type force_generate: bool
    :return:
    """
    # If a normal tier already exists, return it.
    normal_tier = xigt_find(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:NORM_STATE})


    # Otherwise, create a new one, with only L, G and T lines.
    if force_generate or (normal_tier is None and generate):

        if normal_tier is not None:
            inst.remove(normal_tier)

        normal_tier = Tier(id = NORM_ID, type=ODIN_TYPE,
                           attributes={STATE_ATTRIBUTE:NORM_STATE, ALIGNMENT:generate_clean_tier(inst).id})

        # Get one item per...
        add_normal_line_to_tier(inst, normal_tier, ODIN_LANG_TAG, clean_lang_string if clean else lambda x: x)
        add_normal_line_to_tier(inst, normal_tier, ODIN_GLOSS_TAG, clean_gloss_string if clean else lambda x: x)
        add_normal_line_to_tier(inst, normal_tier, ODIN_TRANS_TAG, clean_trans_string if clean else lambda x: x)

        # -------------------------------------------
        # Now, remove the whitespace shared between lines.
        # -------------------------------------------
        textlines = strip_leading_whitespace([i.text for i in normal_tier])
        for textline, item in zip(textlines, normal_tier):
            item.text = textline

        inst.append(normal_tier)
        return normal_tier

    elif normal_tier is not None:
        return normal_tier

    else:
        return None


def generate_clean_tier(inst, merge=False, generate=True, force_generate=False):
    """
    If the clean odin tier exists, return it. Otherwise, create it.

    """

    # -------------------------------------------
    # Search for the clean tier
    # -------------------------------------------
    clean_tier = xigt_find(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:CLEAN_STATE})

    # Remove the clean tier if we are regenerating.
    if clean_tier is not None and force_generate:
        inst.remove(clean_tier)

    # -------------------------------------------
    # If we want to force regenerate the tier, or
    # it is not found and we want to generate it
    # freshly.
    # -------------------------------------------
    if force_generate or ((clean_tier is None) and generate):
        # Otherwise, we will make our own:
        raw_tier = get_raw_tier(inst)


        # Initialize the clean tier...
        clean_tier = Tier(id = CLEAN_ID, type=ODIN_TYPE,
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

            # If there is only one line for the given tag,
            # simply return the first line.
            if len(lines) == 1:
                text = lines[0].value()
                new_tag = lines[0].attributes[ODIN_TAG_ATTRIBUTE]
                align_id = lines[0].id
                item_judgment = lines[0].attributes.get(ODIN_JUDGMENT_ATTRIBUTE)

            # If there are multiple lines for a given tag,
            # concatenate them to a single line.
            elif len(lines) > 1:
                TIER_LOG.info('Corruption detected in instance %s: %s' % (inst.id, [l.attributes['tag'] for l in lines]))
                for l in lines:
                    TIER_LOG.debug('BEFORE: %s' % l)

                # The new text should be the concatenation of the multiple lines...
                text = concat_lines([l.value() for l in lines if l.value() is not None])
                TIER_LOG.debug('AFTER: %s' % text)
                new_tag = primary_tag
                align_id = ','.join([l.id for l in lines])

                item_judgment = None
                for l in lines:
                    j = l.attributes.get(ODIN_JUDGMENT_ATTRIBUTE)
                    if j is not None:
                        item_judgment = j
                        break

            # Set up the attributes for the new line
            item_attributes = {ODIN_TAG_ATTRIBUTE: new_tag}

            # If we have a judgment, add it to the attributes.
            # Otherwise, don't add it.
            if item_judgment is not None:
                item_attributes[ODIN_JUDGMENT_ATTRIBUTE] = item_judgment



            item = Item(id=ask_item_id(clean_tier),
                        alignment=align_id, text=text,
                        attributes=item_attributes)
            clean_tier.add(item)

        inst.append(clean_tier)
        return clean_tier

    # -------------------------------------------
    # Finally, if the tier exists
    # -------------------------------------------
    elif clean_tier is not None:
        return clean_tier

    # -------------------------------------------
    # Otherwise, just return None
    # -------------------------------------------
    else:
        return None


def add_normal_line_to_tier(inst, tier, tag, func):
    """
    Given
    :param inst:
    :param tier:
    :param tag:
    :param func:
    """
    clean_tier = generate_clean_tier(inst)
    clean_lines = [l for l in clean_tier if tag in l.attributes[ODIN_TAG_ATTRIBUTE].split('+')]

    if len(clean_lines) > 1:
        raise XigtFormatException("Clean tier should not have multiple lines of same tag.")

    # If there are clean lines for this tag... There must be only 1...
    # create it and add it to the tier.
    elif clean_lines:

        attributes = {ODIN_TAG_ATTRIBUTE:clean_lines[0].attributes[ODIN_TAG_ATTRIBUTE]}

        cl = clean_lines[0]
        text = None if cl.value() is None else func(cl.value())
        text, j = (None, None) if text is None else extract_judgment(text)

        # -------------------------------------------
        # Several options for the judgment attribute...
        # -------------------------------------------
        # 1) It was previously there on the clean tier.
        #    in this case, carry it over to the normalized
        #    tier.
        line_judgment = cl.attributes.get(ODIN_JUDGMENT_ATTRIBUTE)
        if line_judgment is not None:
            attributes[ODIN_JUDGMENT_ATTRIBUTE] = line_judgment

        # -------------------------------------------
        # 2) After being cleaned, there is still a judgment
        #    character on the line. Extract it and add
        #    the appropriate attribute.
        elif text is not None and j is not None:
            attributes[ODIN_JUDGMENT_ATTRIBUTE] = j

        item = Item(id=gen_item_id(tier.id, len(tier)),
                    text=func(text),
                    alignment=clean_lines[0].id,
                    attributes=attributes)

        tier.add(item)





# -------------------------------------------
# Create morpheme-level tiers
# -------------------------------------------
def words_to_morph_tier(tier, type, id, aln_attribute):
    """
    :param tier:
     :type tier: Tier

    :param type:
    :param id:
    :param aln_attribute:
    """

    mt = Tier(id=id, attributes={aln_attribute:tier.id}, type=type)

    # Go through each word...
    for word in tier:

        morphs = tokenize_item(word, morpheme_tokenizer)

        for morph in morphs:
            # If there is only one morph in the tokenization, don't bother with the indexing, just
            # use the id.
            if len(morphs) == 1:
                aln_str = word.id
            else:
                aln_str = create_aln_expr(word.id, morph.start, morph.stop)

            rm = Item(id=gen_item_id(mt.id, len(mt)),
                      attributes={aln_attribute: aln_str})
            mt.append(rm)

    return mt

# -------------------------------------------
# POS TAG RETRIEVAL
# -------------------------------------------

def lang_tag_tier(inst, tag_method=None):
    return pos_tag_tier(inst, lang(inst).id, tag_method=tag_method)

def gloss_tag_tier(inst, tag_method=None):
    return pos_tag_tier(inst, gloss(inst).id, tag_method=tag_method)

def trans_tag_tier(inst, tag_method=None):
    return pos_tag_tier(inst, trans(inst).id, tag_method=tag_method)

def pos_tag_tier(inst, tier_id, tag_method = None):
    """
    Retrieve the pos tags if they exist for the given tier id...

    :rtype : Tier
    :param tier_id: Id for the tier to find tags for
    :type tier_id: str
    """

    # Also, if we have specified a tag_method we are looking for, then
    # check the metadata to see if the source is correct.
    filters = []
    if tag_method is not None:
        filters = [lambda x: get_intent_method(x) == tag_method]

    pos_tier = xigt_find(inst, alignment=tier_id, type=POS_TIER_TYPE, others = filters)

    return pos_tier

def pos_tags(inst, tier_id, tag_method = None):
    ptt = pos_tag_tier(inst, tier_id, tag_method=tag_method)
