import logging

from intent.igt.consts import ODIN_JUDGMENT_ATTRIBUTE
from intent.igt.igtutils import rgencode, get_judgment, extract_judgment
from unittest import TestCase

from intent.igt.igtutils import strip_leading_whitespace
from intent.igt.search import normalized_tier, cleaned_tier
from intent.utils.dicts import DefaultOrderedDict
import xigt.xigtpath as xp
from xigt.consts import ALIGNMENT

CREATE_LOG = logging.getLogger("IGT_CREATION")


# -------------------------------------------
# Add
# -------------------------------------------


def create_text_tier_from_lines(inst, lines, id_base, state):
    """
    Given a list of lines that are dicts with the attributes 'text' and 'tag', create
    a text tier of the specified type with the provided line items.

    :type lines: list[dict]
    """
    # -------------------------------------------
    # 1) Generate the parent tier.
    tier = RGTier(id=gen_tier_id(inst, id_base), type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:state})


    # -------------------------------------------
    # 2) Iterate over the list of lines
    for line in lines:

        # Make sure the line is a dict.
        if not hasattr(line, 'get') or 'text' not in line or 'tag' not in line:
            raise RGXigtException("When constructing tier from lines, must be a list of dicts with keys 'text' and 'tag'.")

        # Construct the list of tags.
        alltags = []
        if line.get('tag') is not None:
            alltags.append(line.get('tag'))
        if line.get('labels') is not None and line.get('labels'):
            alltags.append(line.get('labels'))
        tag_str = '+'.join(alltags)

        # Construct the attributes
        line_attributes = {ODIN_TAG_ATTRIBUTE:tag_str}
        if line.get('judgment') is not None:
            line_attributes[ODIN_JUDGMENT_ATTRIBUTE] = line['judgment']

        l = RGItem(id=gen_item_id(tier.id, len(tier)),
                   attributes=line_attributes,
                   text=line.get('text'))
        tier.append(l)
    return tier

def add_text_tier_from_lines(inst, lines, id_base, state):
    tier = create_text_tier_from_lines(inst, lines, id_base, state)
    inst.append(tier)

# -------------------------------------------
#
# -------------------------------------------
def add_normal_line_to_tier(inst, tier, tag, func):
    clean_tier = get_clean_tier(inst)
    clean_lines = [l for l in clean_tier if tag in l.attributes[ODIN_TAG_ATTRIBUTE].split('+')]

    if len(clean_lines) > 1:
        PARSELOG.warning(rgencode(clean_tier))
        raise XigtFormatException("Clean tier should not have multiple lines of same tag.")

    # If there are clean lines for this tag... There must be only 1...
    # create it and add it to the tier.
    elif clean_lines:

        attributes = {ODIN_TAG_ATTRIBUTE:clean_lines[0].attributes[ODIN_TAG_ATTRIBUTE]}

        cl = clean_lines[0]
        text = cl.value()

        # Keep the previous judgment if specified, otherwise, look
        # to see if it's been added since.
        line_judgment = cl.attributes.get(ODIN_JUDGMENT_ATTRIBUTE)
        if line_judgment is not None:
            attributes[ODIN_JUDGMENT_ATTRIBUTE] = line_judgment
        elif cl.value() is not None and get_judgment(cl.value()) is not None:
            text, j = extract_judgment(text)
            attributes[ODIN_JUDGMENT_ATTRIBUTE] = get_judgment(cl.value())

        item = RGLine(id=gen_item_id(tier.id, len(tier)),
                    text=func(text),
                    alignment=clean_lines[0].id,
                    attributes=attributes)

        tier.add(item)

def from_raw_text(string, corpus=None, idnum=None):
    """
    Method to create an IGT instance from a raw three lines of text, assuming L-G-T.

    :param string:
    :param corpus:
    :param idnum:
    """
    lines = string.split('\n')
    if len(lines) < 3:
        raise RawTextParseError("Three lines are assumed for raw text. Instead got {}".format(len(lines)))


    if idnum is not None:
        id = gen_item_id('i', idnum)
    elif corpus:
        id = corpus.askIgtId()
    else:
        corpus = RGCorpus()
        id = corpus.askIgtId()

    inst = RGIgt(id = id)
    rt = RGLineTier(id = RAW_ID, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE}, igt=inst)

    for i, l in enumerate(lines):

        # If we have four lines, assume that the first is
        # native orthography
        if len(lines) == 4:
            if i == 0:
                linetag = ODIN_LANG_TAG + '+FR'
            if i == 1:
                linetag = ODIN_LANG_TAG
            if i == 2:
                linetag = ODIN_GLOSS_TAG
            if i == 3:
                linetag = ODIN_TRANS_TAG

        elif len(lines) == 3:
            if i == 0:
                linetag = ODIN_LANG_TAG
            elif i == 1:
                linetag = ODIN_GLOSS_TAG
            elif i == 2:
                linetag = ODIN_TRANS_TAG

        elif len(lines) == 2:
            if i == 0:
                linetag = ODIN_LANG_TAG
            if i == 1:
                linetag = ODIN_TRANS_TAG

        else:
            raise RawTextParseError("Unknown number of lines...")

        if not l.strip():
            raise RawTextParseError("The {} line is empty: {}".format(linetag, l))

        li = RGLine(id=rt.askItemId(), text=l, attributes={'tag':linetag})
        rt.append(li)

    inst.append(rt)
    try:
        inst.basic_processing()
    except GlossLangAlignException as glae:
        CONVERT_LOG.warn('Gloss and language lines could not be automatically aligned for instance "{}".'.format(inst.id))

        # CONVERT_LOG.warn("Basic processing failed for instance {}".format(inst.id))
    return inst

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

def get_normal_tier(inst, clean=True, generate=True, force_generate=False):
    """
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
    normal_tier = find_in_obj(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:NORM_STATE})


    # Otherwise, create a new one, with only L, G and T lines.
    if force_generate or (normal_tier is None and generate):

        if normal_tier is not None:
            inst.remove(normal_tier)

        normal_tier = RGLineTier(id = NORM_ID, type=ODIN_TYPE,
                                 attributes={STATE_ATTRIBUTE:NORM_STATE, ALIGNMENT:get_clean_tier(inst).id})

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

def get_clean_tier(inst, merge=False, generate=True, force_generate=False):
    """
    If the clean odin tier exists, return it. Otherwise, create it.

    """

    # -------------------------------------------
    # Search for the clean tier
    # -------------------------------------------
    clean_tier = find_in_obj(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:CLEAN_STATE})

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
                PARSELOG.info('Corruption detected in instance %s: %s' % (inst.id, [l.attributes['tag'] for l in lines]))
                for l in lines:
                    PARSELOG.debug('BEFORE: %s' % l)

                # The new text should be the concatenation of the multiple lines...
                text = concat_lines([l.value() for l in lines])
                PARSELOG.debug('AFTER: %s' % text)
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



            item = RGLine(id=clean_tier.askItemId(),
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

def replace_lines(inst, clean_lines, norm_lines):
    """
    Given an instance and a list of clean lines and normal lines,
    add a cleaned tier and normalized if they do not already exist,
    otherwise, replace them.

    :param inst:
    :type inst: xigt.Igt
    :param clean_lines:
    :type clean_lines: list[dict]
    :param norm_lines:
    :type norm_lines: list[dict]
    """

    # -------------------------------------------
    # Remove the old clean/norm lines.
    # -------------------------------------------
    old_clean_tier = cleaned_tier(inst)
    if old_clean_tier is not None:
        inst.remove(old_clean_tier)

    old_norm_tier = normalized_tier(inst)
    if old_norm_tier is not None:
        inst.remove(old_norm_tier)

    # -------------------------------------------
    # Now, add the clean/norm lines, if provided.
    # -------------------------------------------
    if clean_lines:
        new_clean_tier = create_text_tier_from_lines(inst, clean_lines, CLEAN_ID, CLEAN_STATE)
        inst.append(new_clean_tier)

    if norm_lines:
        new_norm_tier = create_text_tier_from_lines(inst, norm_lines, NORM_ID, NORM_STATE)
        inst.append(new_norm_tier)

    return inst



from .consts import RAW_ID, ODIN_TYPE, STATE_ATTRIBUTE, RAW_STATE, ODIN_LANG_TAG, ODIN_GLOSS_TAG, \
    ODIN_TRANS_TAG, ODIN_TAG_ATTRIBUTE
from .rgxigt import RGCorpus, RGIgt, RGLineTier, RGLine,  CONVERT_LOG, RGTier, gen_tier_id, RGItem, PARSELOG, \
    gen_item_id
from .exceptions import GlossLangAlignException, RawTextParseError, RGXigtException, XigtFormatException

from .search import find_in_obj, raw_tier
from .consts import *
from .igtutils import merge_lines, clean_lang_string, clean_gloss_string, clean_trans_string, concat_lines
from .rgxigt import RGLineTier, PARSELOG, RGLine, RGTier, NoODINRawException
from .creation import *