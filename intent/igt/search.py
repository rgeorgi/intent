# -------------------------------------------
# FILTERS
# -------------------------------------------
import re

import logging

from intent.trees import IdTree
from xigt.errors import XigtStructureError
from xigt.ref import selection_re, span_re, ids

RETRIEVE_LOG = logging.getLogger("RETRIEVAL")
from intent.alignment.Alignment import Alignment
from intent.consts import *

from intent.igt.exceptions import NoNormLineException, MultipleNormLineException, NoTransLineException, \
    NoGlossLineException, NoLangLineException
from intent.igt.metadata import get_intent_method
from xigt import ref, Tier, Item, Igt
from xigt.consts import CONTENT, ALIGNMENT
from xigt.consts import SEGMENTATION
from xigt.mixins import XigtContainerMixin



def get_id_base(id_str):
    """
    Return the "base" of the id string. This should either be everything leading up to the final numbering, or a hyphen-separated letter.

    :param id_str:
    :type id_str:
    """
    s = re.search('^(\S+?)(?:[0-9]+|-[a-z])?$', id_str).group(1)
    return s

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

# -------------------------------------------
# FIND
# -------------------------------------------

def _find_in_self(obj, filters=list):
    """
    Check to see if this object matches all of the filter functions in filters.

    :param filters: List of functions to apply to this object. All filters have a logical and
                    applied to them.
    :type filters: list
    """

    assert len(filters) > 0, "Must have selected some attribute to filter."

    # Iterate through the filters...
    for filter in filters:
        if not filter(obj): # If one evaluates to false...
            return None      # ..we're done. Exit with "None"

    # If we make it through all the iteration, we're a match. Return.
    return obj

def _build_filterlist(**kwargs):
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
        elif kw == 'alignment':
            filters += [aln_match(val)]

        elif kw == 'others': # Append any other filters...
            filters += val
        else:
            raise ValueError('Invalid keyword argument "%s"' % kw)

    return filters

def find_in_obj(obj, **kwargs):
    found = _find_in_self(obj, _build_filterlist(**kwargs))
    if found is not None:
        return obj

    # If we are working on a container object, iterate
    # over its children.
    elif isinstance(obj, XigtContainerMixin):
        found = None
        for child in obj:
            found = find_in_obj(child, **kwargs)
            if found is not None:
                break
        return found

def findall_in_obj(obj, **kwargs):
    found = []
    found_item = _find_in_self(obj, _build_filterlist(**kwargs))
    if found_item is not None:
        found = [found_item]

    # If we are working on a container object, iterate over
    # the children.
    if isinstance(obj, XigtContainerMixin):
        for child in obj:
            found += findall_in_obj(child, **kwargs)


    return found

# -------------------------------------------
# Some convenience methods for common searches
# -------------------------------------------
def text_tier(inst, state):
    return find_in_obj(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:state})

def raw_tier(inst) -> Tier:
    return text_tier(inst, RAW_STATE)

def cleaned_tier(inst) -> Tier:
    return text_tier(inst, CLEAN_STATE)

def normalized_tier(inst) -> Tier:
    return text_tier(inst, NORM_STATE)

# -------------------------------------------
# More convenience methods
# -------------------------------------------
def _handle_nnle(f):
    try:
        return f()
    except (NoNormLineException, MultipleNormLineException) as nnle:
        return None

def lang_line(inst) -> Item:
    return _handle_nnle(lambda: retrieve_normal_line(inst, ODIN_LANG_TAG))

def gloss_line(inst) -> Item:
    return _handle_nnle(lambda: retrieve_normal_line(inst, ODIN_GLOSS_TAG))

def trans_line(inst) -> Item:
    return _handle_nnle(lambda: retrieve_normal_line(inst, ODIN_TRANS_TAG))




# -------------------------------------------
# Specific tiers.
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
    return _word_tier(inst, retrieve_lang_words, NoLangLineException)

def gloss(inst) -> Tier:
    return _word_tier(inst, retrieve_gloss_words, NoGlossLineException)

def trans(inst) -> Tier:
    return _word_tier(inst, retrieve_trans_words, NoTransLineException)

def morphemes(inst) -> Tier:
    mt = find_in_obj(inst, type=LANG_MORPH_TYPE)
    if mt is None:
        mt = words_to_morph_tier(lang(inst), LANG_MORPH_TYPE, LANG_MORPH_ID, SEGMENTATION)
        inst.append(mt)
    return mt

def glosses(inst) -> Tier:
    # Make sure that we don't pick up the gloss-word tier by accident.
    f = [lambda x: not is_word_level_gloss(x)]

    gt = find_in_obj(inst, type=GLOSS_MORPH_TYPE, others=f)


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

# -------------------------------------------
# Other tier types.
# -------------------------------------------
def get_ps_tier(inst, target):
    return find_in_obj(inst, type=PS_TIER_TYPE, alignment=target.id)

def get_ps(inst, target) -> IdTree:
    t = get_ps_tier(inst, target)
    if t is not None:
        return read_pt(t)

def get_lang_ps(inst):
    return get_ps(inst, lang(inst))

def get_trans_ps(inst):
    return get_ps(inst, trans(inst))

def get_ds_tier(inst, dep):
    return find_in_obj(inst, type=DS_TIER_TYPE, attributes={DS_DEP_ATTRIBUTE:dep.id})

def get_ds(inst, target, pos_source=None):
    t = get_ds_tier(inst, target)
    if t is not None:
        return read_ds(t, pos_source=pos_source)

def get_lang_ds(inst, pos_source=None):
    return get_ds(inst, lang(inst), pos_source)

def get_trans_ds(inst, pos_source=None):
    return get_ds(inst, trans(inst), pos_source)

def get_trans_parse_tier(inst):
    """
    Get the phrase structure tier aligned with the translation words.
    """
    return find_in_obj(inst, type=PS_TIER_TYPE, attributes={ALIGNMENT:trans(inst).id})

def get_pos_tags(inst, tier_id, tag_method = None):
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

    pos_tier = find_in_obj(inst, alignment=tier_id, type=POS_TIER_TYPE, others = filters)

    return pos_tier


# -------------------------------------------
# Alignment Retrieval
# -------------------------------------------
def get_bilingual_alignment_tier(inst, src_id, tgt_id, aln_method = None):
    # Look for a previously created alignment of the same type.
    attributes = {SOURCE_ATTRIBUTE:src_id, TARGET_ATTRIBUTE:tgt_id}

    # Also add some search filters to match the metadata information, so that
    # we don't overwrite alignments provided by other sources.
    filters = []
    if aln_method is not None:
        filters = [lambda x: get_intent_method(x) == aln_method]

    ba_tier = find_in_obj(inst, attributes=attributes, others=filters)
    return ba_tier

def item_index(item):
    """
    Retrieve the index of a given item on its parent tier.

    :type item: Item
    """
    return list(item.tier).index(item)+1

def delete_tier(tier):
    tier.igt.remove(tier)

def get_bilingual_alignment(inst, src_id, tgt_id, aln_method = None):
    """
    :type inst: Igt
    :param inst:
    :param src_id:
    :param tgt_id:
    :param aln_method:
    """
    ba_tier = get_bilingual_alignment_tier(inst, src_id, tgt_id, aln_method = aln_method)

    if ba_tier is not None:
        a = Alignment(type=get_intent_method(ba_tier))
        for ba in ba_tier:
            src_id = ba.attributes[SOURCE_ATTRIBUTE]
            tgt_id = ba.attributes[TARGET_ATTRIBUTE]

            src_item = find_in_obj(inst, id=src_id)
            tgt_ids = ref.ids(tgt_id)
            for tgt in tgt_ids:
                tgt_item = find_in_obj(inst, id=tgt_id)

                if tgt_item is not None:
                    a.add((item_index(src_item), item_index(tgt_item)))
                else:
                    RETRIEVE_LOG.warn('Instance {} had target ID "{}", but no such ID was found.'.format(inst.id, tgt_id))

        return a



def get_trans_gloss_alignment(inst, aln_method=None):
    # -------------------------------------------
    # 1) If we already have this alignment, just return it.
    trans_gloss = get_bilingual_alignment(inst, trans(inst).id, gloss(inst).id, aln_method)
    trans_glosses = get_bilingual_alignment(inst, trans(inst).id, glosses(inst).id, aln_method)

    if trans_gloss is not None:
        return trans_gloss

    # -------------------------------------------
    # 2) Otherwise, if we have alignment between the translation line
    #    and the morpheme-level glosses, let's return a new
    #    alignment created from these.
    elif trans_glosses is not None:
        new_trans_gloss = Alignment(type=trans_glosses.type)

        for trans_i, gloss_i in trans_glosses:
            gloss_m = glosses(inst)[gloss_i-1]
            gloss_w = find_gloss_word(inst, gloss_m)

            new_trans_gloss.add((trans_i, item_index(gloss_w)))

        return new_trans_gloss

    # -------------------------------------------
    # 3) Otherwise, return None.
    else:
        return None

def get_trans_glosses_alignment(inst, aln_method=None):
    return get_bilingual_alignment(trans(inst).id, glosses(inst).id, aln_method=aln_method)

def get_trans_gloss_wordpairs(inst, aln_method=None, all_morphs=True):
    """
    Return a list of (trans_word, gloss_morph) pairs

    :param aln_method:
    :return:
     :rtype: list[tuple]
    """
    pairs = []

    # Use whichever method of selecting alignment to choose
    # the alignment method
    def select_a(func):
        a = None

        # If a list was provided as an argument to aln_method,
        # treat it as a list of priorities to search for alignment
        # with.
        if isinstance(aln_method, list):
            for method in aln_method:
                a = func(method)
                if a is not None:
                    break
        return a

    if all_morphs:

        a = select_a(lambda x: get_trans_gloss_alignment(inst, aln_method=x))
        if a is not None:
            for t_i, g_i in a:
                t_w = trans(inst)[t_i - 1]
                g_w = gloss(inst)[g_i - 1]
                g_ms = find_glosses(inst, g_w)
                pairs.append((t_w.value(), ' '.join([g_m.value() for g_m in g_ms])))
                # for g_m in g_ms:
                #     pairs.append((t_w.value(), g_m.value()))
    else:
        a = select_a(lambda x: get_trans_glosses_alignment(inst, aln_method=x))
        if a is not None:
            for t_i, g_i in a:
                t_w = trans(inst)[t_i - 1]   # Remember that indexed-by-one...
                g_m = glosses(inst)[g_i - 1]
                pairs.append((t_w.value(), g_m.value()))

    return pairs

def find_glosses(inst, gloss_word):
    """
    Given a gloss word, attempt to find all the glosses that segment it.

    :param inst:
    :type inst: RGIgt
    :param gloss_word:
    :type gloss_word: RGWord
    """

    # This filter should find elements that have a content tag that has
    others = [lambda x: gloss_word.id in ids(x.attributes.get(CONTENT, ''))]
    return findall_in_obj(inst, others=others)

def get_gloss_lang_alignment(inst):
    """
    Convenience method for getting the gloss-word to lang-word
    token based alignment
    """
    return get_aligned_tokens(gloss(inst))

def get_aligned_tokens(tier):
    """
    :type tier: Tier
    """
    a = Alignment()
    for item in tier:
        ia = item.attributes[ALIGNMENT]
        aligned_w = find_in_obj(tier.igt, id=ia)
        a.add((item_index(item), item_index(aligned_w)))
    return a

def get_trans_gloss_lang_alignment(inst, aln_method=None):
    """
    Get the translation to lang alignment, travelling through the gloss line.
    """

    tg_aln = get_trans_gloss_alignment(inst, aln_method=aln_method)

    # -------------------------------------------
    # If we don't have an existing alignment, return None.

    if tg_aln is None:
        return None

    else:
        gl_aln = get_gloss_lang_alignment(inst)

        # Combine the two alignments...
        a = Alignment(type=tg_aln.type)
        for t_i, g_i in tg_aln:
            l_js = [l_j for (g_j, l_j) in gl_aln if g_j == g_i]
            for l_j in l_js:
                a.add((t_i, l_j))
        return a

def get_trans_gloss_lang_aligned_pairs(inst, aln_method=None):
    """
    Retrieve the word pairs that are aligned via the specified aln_method.
    """
    ret_pairs = []
    for t_i, l_j in get_trans_gloss_lang_alignment(inst, aln_method=aln_method):
        ret_pairs.append((trans(inst)[t_i - 1],
                          lang(inst)[l_j - 1]))
    return ret_pairs

import logging

from intent.consts import *
from intent.igt.metadata import set_intent_method
from intent.igt.metadata import set_intent_proj_data
from intent.igt.search import raw_tier, find_in_obj, cleaned_tier, normalized_tier
from intent.utils.dicts import DefaultOrderedDict
from intent.utils.token import tokenize_item, morpheme_tokenizer, Token
from xigt.consts import ALIGNMENT
from xigt.model import Tier, Item

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
    tier = Tier(id=gen_tier_id(inst, id_base), type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:state})


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

        l = Item(id=gen_item_id(tier.id, len(tier)),
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

        li = Item(id=rt.askItemId(), text=l, attributes={'tag':linetag})
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

        normal_tier = Tier(id = NORM_ID, type=ODIN_TYPE,
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
                PARSELOG.info('Corruption detected in instance %s: %s' % (inst.id, [l.attributes['tag'] for l in lines]))
                for l in lines:
                    PARSELOG.debug('BEFORE: %s' % l)

                # The new text should be the concatenation of the multiple lines...
                text = concat_lines([l.value() for l in lines if l.value() is not None])
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
# Create Phrase Tier
# -------------------------------------------
def create_pt_tier(inst, phrase_tree, w_tier, parse_method=None, source_tier=None, aln_type=None):
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
    pt_id = gen_tier_id(inst, PS_TIER_ID, tier_type=PS_TIER_TYPE, alignment=w_tier.id)
    pt_tier = Tier(type=PS_TIER_TYPE,
                   id=pt_id,
                   alignment=w_tier.id,
                   attributes={PS_CHILD_ATTRIBUTE:pt_id})

    # 2) Add the intent metadata...
    set_intent_method(pt_tier, parse_method)
    if source_tier is not None:
        set_intent_proj_data(pt_tier, source_tier, aln_type)

    phrase_tree.assign_ids(pt_tier.id)

    # We should get back the same number of tokens as we put in
    assert len(phrase_tree.leaves()) == len(w_tier)

    leaves = list(phrase_tree.leaves())
    preterms = list(phrase_tree.preterminals())

    assert len(leaves) == len(preterms)

    # 2) Now, run through the leaves and the preterminals ------------------
    for wi, preterm in zip(w_tier, preterms):

        # Note that the preterminals align with a given word...
        pi = Item(id=preterm.id, alignment=wi.id, text=preterm.label())
        pt_tier.append(pi)

    # 3) Finally, run through the rest of the subtrees. --------------------
    for st in phrase_tree.nonterminals():
        child_refs = ' '.join([s.id for s in st])
        si = Item(id=st.id, attributes={PS_CHILD_ATTRIBUTE:child_refs}, text=st.label())
        pt_tier.append(si)

    # 4) And add the created tier to this instance. ------------------------
    inst.append(pt_tier)

def create_dt_tier(inst, dt, w_tier, parse_method=None, source_tier=None, aln_type=None):
    """
    Create the dependency structure tier based on the ds that is passed in. The :class:`intent.trees.DepTree`
    structure that is passed in must be based on the words in the translation line, as the indices from the
    dependency tree will be used to identify the tokens.

    :param dt: Dependency tree to create a tier for.
    :type dt: DepTree
    """

    # 1) Start by creating dt tier -----------------------------------------
    dt_tier = Tier(type=DS_TIER_TYPE,
                   id=gen_tier_id(inst, DS_TIER_ID, DS_TIER_TYPE, alignment=w_tier.id),
                   attributes={DS_DEP_ATTRIBUTE: w_tier.id, DS_HEAD_ATTRIBUTE: w_tier.id})

    set_intent_method(dt_tier, parse_method)
    if source_tier is not None:
        set_intent_proj_data(dt_tier, source_tier, aln_type)


    # 2) Next, simply iterate through the tree and make the head/dep mappings.


    for label, head_i, dep_i in dt.indices_labels():
        attributes={DS_DEP_ATTRIBUTE:w_tier[dep_i-1].id}

        if head_i != 0:
            attributes[DS_HEAD_ATTRIBUTE] = w_tier[head_i-1].id


        di = Item(id=ask_item_id(dt_tier), attributes=attributes, text=label)
        dt_tier.append(di)

    inst.append(dt_tier)

def tier_tokens(tier):
    """
    :param tier:
     :type tier: Tier
    :return:
    """
    return [Token(i.value(), index=item_index(i)) for i in tier]

def tier_text(tier, remove_whitespace_inside_tokens = True, return_list=False):
    tokens = [str(i) for i in tier_tokens(tier)]
    if remove_whitespace_inside_tokens:
        # TODO: Another whitespace replacement handling
        tokens = [re.sub('\s+','',i) for i in tokens]
    if return_list:
        return tokens
    else:
        return ' '.join(tokens)


def gen_item_id(id_base, num):
    return '{}{}'.format(id_base, num+1)

def ask_item_id(tier):
    return gen_item_id(tier.id, len(tier))

def resolve_objects(container, expression):
    """
    Return the string that is the resolution of the alignment expression
    `expression`, which selects ids from `container`.
    """
    itemgetter = getattr(container, 'get_item', container.get)
    tokens = []
    expression = expression.strip()
    for sel_delim, _id, _range in selection_re.findall(expression):

        item = find_in_obj(container, id=_id)
        if item is None:
            raise XigtStructureError(
                'Referred Item (id: {}) from reference "{}" does not '
                'exist in the given container.'
                .format(_id, expression)
            )

        if _range:
            for spn_delim, start, end in span_re.findall(_range):
                start = int(start) if start else None
                end = int(end) if end else None
                tokens.append((item, (start, end)))
        else:
            tokens.append((item, None))
    return tokens



# -------------------------------------------
# Imports

from .exceptions import RGXigtException, RawTextParseError, XigtFormatException, GlossLangAlignException, \
    NoODINRawException, project_creator_except
from .igtutils import extract_judgment, rgencode, clean_lang_string, clean_gloss_string, clean_trans_string, \
    strip_leading_whitespace, concat_lines, rgp
from .rgxigt import RGCorpus, PARSELOG, RGIgt, RGLineTier, CONVERT_LOG, \
    RGMorphTier, create_aln_expr, gen_tier_id, read_pt, read_ds

from .rgxigt import retrieve_lang_words, is_word_level_gloss, retrieve_normal_line, retrieve_trans_words, retrieve_gloss_words, remove_word_level_info, \
    add_word_level_info, find_gloss_word