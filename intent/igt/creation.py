import logging

from intent.igt.igtutils import rgencode

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

        alltags = '+'.join([line.get('tag')] + [line.get('labels')])

        l = RGItem(id=gen_item_id(tier.id, len(tier)),
                   attributes={ODIN_TAG_ATTRIBUTE:alltags},
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
        item = RGLine(id=gen_item_id(tier.id, len(tier)),
                    text=func(clean_lines[0].value()),
                    alignment=clean_lines[0].id,
                    attributes={ODIN_TAG_ATTRIBUTE:clean_lines[0].attributes[ODIN_TAG_ATTRIBUTE]})

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

from .consts import RAW_ID, ODIN_TYPE, STATE_ATTRIBUTE, RAW_STATE, ODIN_LANG_TAG, ODIN_GLOSS_TAG, \
    ODIN_TRANS_TAG, ODIN_TAG_ATTRIBUTE
from .rgxigt import RGCorpus, RGIgt, RGLineTier, RGLine,  CONVERT_LOG, RGTier, gen_tier_id, RGItem, PARSELOG, \
    gen_item_id
from .exceptions import GlossLangAlignException, RawTextParseError, RGXigtException, XigtFormatException
from .xigt_manipulations import get_clean_tier