from intent.consts import *
from intent.igt.exceptions import RawTextParseError, GlossLangAlignException
from intent.igt.references import gen_item_id, ask_item_id
from intent.utils.string_utils import replace_invalid_xml
from intent.utils.token import whitespace_tokenizer, tokenize_string
from xigt.model import XigtCorpus, Igt, Tier, Item

import logging
PARSELOG = logging.getLogger("TEXTPARSER")

def raw_txt_to_xc(cls, txt):
    """

    :rtype: XigtCorpus
    """
    print("Creating XIGT corpus from raw text...")
    xc = XigtCorpus()

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
        i = raw_txt_to_inst(instance, corpus=xc)
        xc.append(i)


    print("{} instances parsed.".format(len(xc)))
    return xc

def raw_txt_to_inst(string, corpus=None, idnum=None):
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
        corpus = XigtCorpus()
        id = 'i{}'.format(len(corpus))

    inst = Igt(id = id)
    rt = Tier(id = RAW_ID, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE}, igt=inst)

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

        li = Item(id=ask_item_id(rt), text=l, attributes={'tag':linetag})
        rt.append(li)

    inst.append(rt)
        # CONVERT_LOG.warn("Basic processing failed for instance {}".format(inst.id))
    return inst

def create_words_tier_from_string(string):
    tokens = tokenize_string(string, tokenizer=whitespace_tokenizer)
    wt = Tier(type=WORDS_TYPE)
    for token in tokens:
        i = Item(id=ask_item_id(wt), text=token.value())
        wt.append(i)
    return wt