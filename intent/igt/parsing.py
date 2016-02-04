import re

from intent.igt.igt_functions import basic_processing
from xigt.codecs import xigtxml

from intent.consts import *
from intent.igt.create_tiers import trans_lines
from intent.igt.exceptions import RawTextParseError, GlossLangAlignException, NoTransLineException, NoGlossLineException, \
    NoLangLineException
from intent.igt.references import gen_item_id, ask_item_id
from intent.utils.string_utils import replace_invalid_xml
from intent.utils.token import whitespace_tokenizer, tokenize_string
from xigt.consts import INCREMENTAL, FULL
from xigt.model import XigtCorpus, Igt, Tier, Item

import logging
PARSELOG = logging.getLogger("TEXTPARSER")

def xc_load(path, mode=FULL, do_basic_processing=False):
    f = open(path, 'r', encoding='utf-8')
    xc = xigtxml.load(f, mode=mode)
    if do_basic_processing:
        for inst in xc:
            basic_processing(inst)
    return xc

def raw_txt_to_xc(txt):
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

def parse_odin_xc(text, require_trans = True, require_gloss = True, require_lang = True, limit = None):
    """
    Read in a odin-style textfile to create the xigt corpus.

    """
    # Initialize the corpus
    xc = XigtCorpus()

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
            i = parse_odin_inst(inst_txt, corpus=xc, idnum=inst_num)
        except GlossLangAlignException as glae:
            PARSELOG.warn('Gloss and language could not be automatically aligned for instance "%s". Skipping' % gen_item_id('i', inst_num))
            continue

        # Try to get the translation line. ---------------------------------
        try:
            hastrans = trans_lines(i)
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


def parse_odin_inst(string, corpus = None, idnum=None):
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
        corpus = XigtCorpus()
        id = 'i{}'.format(len(corpus))

    inst = Igt(id = id, attributes={'doc-id':docid,
                                    'line-range':'%s %s' % (lnstart, lnstop),
                                    'tag-types':tagtypes})

    # Now, find all the lines
    lines = re.findall('line=([0-9]+)\stag=(\S+):(.*)\n?', string)

    # --- 3) Create a raw tier.
    rt = Tier(id = RAW_ID, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE}, igt=inst)

    for lineno, linetag, linetxt in lines:
        l = Item(id = ask_item_id(rt), text=linetxt, attributes={'tag':linetag, 'line':lineno}, tier=rt)
        rt.append(l)

    inst.append(rt)
    basic_processing(inst)

    return inst

def create_words_tier_from_string(string):
    tokens = tokenize_string(string, tokenizer=whitespace_tokenizer)
    wt = Tier(type=WORDS_TYPE)
    for token in tokens:
        i = Item(id=ask_item_id(wt), text=token.value())
        wt.append(i)
    return wt