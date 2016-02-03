# -------------------------------------------
# FILTERS
# -------------------------------------------
import copy
import re

import logging
from collections import defaultdict

from intent.igt.create_tiers import lang, trans, pos_tag_tier, gloss, glosses, lang_tag_tier, morphemes, generate_clean_tier, \
    generate_normal_tier
from intent.igt.references import xigt_find, ask_item_id, cleaned_tier, normalized_tier, \
    gen_tier_id, odin_ancestor, xigt_findall, gen_item_id, item_index
from intent.interfaces.fast_align import fast_align_sents
from intent.interfaces.giza import GizaAligner
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_parser import StanfordParser
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.pos.TagMap import TagMap
from intent.trees import project_ps, project_ds, Terminal, DepEdge, build_dep_edges, IdTree, DepTree
from intent.utils.env import c, tagger_model, posdict
from intent.utils.token import Token
from xigt.errors import XigtStructureError
from xigt.ref import ids, selection_re, span_re

RETRIEVE_LOG = logging.getLogger("RETRIEVAL")
ALIGN_LOG = logging.getLogger("ALN")

from xigt import Tier, Item, Igt, XigtCorpus
from xigt.consts import SEGMENTATION, ALIGNMENT, CONTENT


# -------------------------------------------
# Specific tiers.
# -------------------------------------------





# -------------------------------------------
# Other tier types.
# -------------------------------------------
def get_ps_tier(inst, target):
    return xigt_find(inst, type=PS_TIER_TYPE, alignment=target.id)

def get_ps(inst, target):
    t = get_ps_tier(inst, target)
    if t is not None:
        return read_pt(t)

def get_lang_ps(inst):
    return get_ps(inst, lang(inst))

def get_trans_ps(inst):
    return get_ps(inst, trans(inst))

def get_ds_tier(inst, dep):
    return xigt_find(inst, type=DS_TIER_TYPE, attributes={DS_DEP_ATTRIBUTE:dep.id})

def get_ds(inst, target, pos_source=None, unk_pos_handling=None):
    t = get_ds_tier(inst, target)
    if t is not None:
        return read_ds(t, pos_source=pos_source, unk_pos_handling=unk_pos_handling)

def get_lang_ds(inst, pos_source=None, unk_pos_handling=None):
    return get_ds(inst, lang(inst), pos_source, unk_pos_handling=unk_pos_handling)

def get_trans_ds(inst, pos_source=None):
    return get_ds(inst, trans(inst), pos_source)

def get_trans_parse_tier(inst):
    """
    Get the phrase structure tier aligned with the translation words.
    """
    return xigt_find(inst, type=PS_TIER_TYPE, attributes={ALIGNMENT:trans(inst).id})


# -------------------------------------------

def add_pos_tags(inst, tier_id, tags, tag_method = None):
    """
    Assign a list of pos tags to the tier specified by tier_id. The number of tags
    must match the number of items in the tier.

    :param tier_id: The id for the tier
    :type tier_id: str
    :param tags: A list of POS tag strings
    :type tags: [str]
    """

    # See if we have a pos tier that's already been assigned by this method.
    prev_tier = pos_tag_tier(inst, tier_id, tag_method=tag_method)

    # And delete it if so.
    if prev_tier: delete_tier(prev_tier)

    # Determine the id of this new tier...
    new_id = gen_tier_id(inst, POS_TIER_ID, alignment=tier_id)

    # Find the tier that we are adding tags to.
    tier = xigt_find(inst, id=tier_id)

    # We assume that the length of the tags we are to add is the same as the
    # number of tokens on the target tier.
    assert len(tier) == len(tags)

    # Create the POS tier
    pt = Tier(type=POS_TIER_TYPE, id=new_id, alignment=tier_id,
              attributes={ALIGNMENT:tier_id})

    # And add the metadata for the source (intent) and tagging method
    set_intent_method(pt, tag_method)

    inst.append(pt)

    # Go through the words and add the tags.
    for w, tag in zip(tier.items, tags):
        p = Item(id=ask_item_id(pt), alignment=w.id, text=tag)
        pt.append(p)


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

    ba_tier = xigt_find(inst, attributes=attributes, others=filters)
    return ba_tier



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

            src_item = xigt_find(inst, id=src_id)
            tgt_ids = ids(tgt_id)
            for tgt in tgt_ids:
                tgt_item = xigt_find(inst, id=tgt_id)

                if tgt_item is not None:
                    a.add((item_index(src_item), item_index(tgt_item)))
                else:
                    RETRIEVE_LOG.warn('Instance {} had target ID "{}", but no such ID was found.'.format(inst.id, tgt_id))

        return a


def get_trans_gloss_alignment(inst, aln_method=None):
    # -------------------------------------------
    # 1) If we already have this alignment, just return it.
    # -------------------------------------------
    """
    Retrieve the alignment between translation and gloss line, travelling through the
    sub-token level "glosses" tokens if necessary.
    """
    trans_gloss = get_bilingual_alignment(inst, trans(inst).id, gloss(inst).id, aln_method)
    trans_glosses = get_bilingual_alignment(inst, trans(inst).id, glosses(inst).id, aln_method)

    if trans_gloss is not None:
        return trans_gloss

    # -------------------------------------------
    # 2) Otherwise, if we have alignment between the translation line
    #    and the morpheme-level glosses, let's return a new
    #    alignment created from these.
    # -------------------------------------------
    elif trans_glosses is not None:
        new_trans_gloss = Alignment(type=trans_glosses.type)

        for trans_i, gloss_i in trans_glosses:
            gloss_m = glosses(inst)[gloss_i-1]
            gloss_w = find_gloss_word(inst, gloss_m)

            new_trans_gloss.add((trans_i, item_index(gloss_w)))

        return new_trans_gloss

    # -------------------------------------------
    # 3) Otherwise, return None.
    # -------------------------------------------
    else:
        return None

def get_trans_glosses_alignment(inst, aln_method=None):
    return get_bilingual_alignment(inst, trans(inst).id, glosses(inst).id, aln_method=aln_method)


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
    return xigt_findall(inst, others=others)

def get_gloss_lang_alignment(inst):
    """
    Convenience method for getting the gloss-word to lang-word
    token based alignment
    """
    return tier_alignment(gloss(inst))

def tier_alignment(tier: Tier):
    """
    Return the alignment that is stored between items and their attributes (e.g. between morphemes
    and glosses).
    """
    a = Alignment()
    for item in tier:
        if ALIGNMENT in item.attributes:
            ia = item.attributes[ALIGNMENT]
            aligned_w = xigt_find(tier.igt, id=ia)
            a.add((item_index(item), item_index(aligned_w)))
    return a

def get_trans_gloss_lang_alignment(inst, aln_method=None):
    """
    Get the translation to lang alignment, travelling through the gloss line.
    """

    # -------------------------------------------
    # 1) Obtain the alignment between translation line
    #    and gloss line, using the specified method.
    # -------------------------------------------
    tg_aln = get_trans_gloss_alignment(inst, aln_method=aln_method)

    # -------------------------------------------
    # 2) If there is no such alignment with the
    #    given method, return None.
    # -------------------------------------------
    if tg_aln is None:
        return None

    # -------------------------------------------
    # 2) If there is an alignment between the
    #    translation line and gloss line, obtain
    #    the alignment between the gloss and language
    #    line, and then return an alignment that maps
    #    translation line to language line directly.
    # -------------------------------------------
    else:
        gl_aln = get_gloss_lang_alignment(inst)

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

def add_raw_tier(inst, lines):
    add_text_tier_from_lines(inst, lines, RAW_ID, RAW_STATE)

def add_clean_tier(inst, lines):
    add_text_tier_from_lines(inst, lines, CLEAN_ID, CLEAN_STATE)

def add_normal_tier(inst, lines):
    add_text_tier_from_lines(inst, lines, NORM_ID, NORM_STATE)

# -------------------------------------------
#
# -------------------------------------------




# -------------------------------------------





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




def resolve_objects(container, expression):
    """
    Return the string that is the resolution of the alignment expression
    `expression`, which selects ids from `container`.
    """
    itemgetter = getattr(container, 'get_item', container.get)
    tokens = []
    expression = expression.strip()
    for sel_delim, _id, _range in selection_re.findall(expression):

        item = xigt_find(container, id=_id)
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
# ALIGNMENT
# -------------------------------------------


from intent.consts import *

def set_bilingual_alignment(inst, src_tier, tgt_tier, aln, aln_method):
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
    prev_ba_tier = get_bilingual_alignment_tier(inst, src_tier.id, tgt_tier.id, aln_method)

    if prev_ba_tier:
        delete_tier(prev_ba_tier)

    # Just to make things neater, let's sort the alignment by src index.
    aln = sorted(aln, key = lambda x: x[0])

    # Start by creating the alignment tier.
    tier_id = gen_tier_id(inst, G_T_ALN_ID, tier_type=ALN_TIER_TYPE)
    ba_tier = Tier(id=tier_id,
                   type=ALN_TIER_TYPE,
                   attributes={SOURCE_ATTRIBUTE:src_tier.id,
                               TARGET_ATTRIBUTE:tgt_tier.id})

    # Add the metadata for the alignment source (intent) and type (giza or heur)
    set_intent_method(ba_tier, aln_method)

    for src_i, tgt_i in aln:
        src_token = src_tier[src_i-1]
        tgt_token = tgt_tier[tgt_i-1]

        add_pair(ba_tier, src_token.id, tgt_token.id)

    inst.append(ba_tier)

def add_pair(tier, src_id, tgt_id):
    attributes = {SOURCE_ATTRIBUTE:src_id, TARGET_ATTRIBUTE:tgt_id}
    i = xigt_find(tier, attributes=attributes)
    if i is None:
        ba = Item(id=ask_item_id(tier), attributes=attributes)
        tier.append(ba)
    else:
        i.attributes[TARGET_ATTRIBUTE] += ',' + tgt_id

def heur_align_corp(xc, **kwargs):
    for inst in xc:
        heur_align_inst(inst, **kwargs)

def heur_align_inst(inst, **kwargs):
    """
    Heuristically align the gloss and translation lines of this instance.

    Has the following effects.

    1) Create bilingual alignment between the translation line and the "glosses" tier.
    :rtype Alignment:
    """

    # If given the "tokenize" option, use the tokens
    # split at the morpheme level

    if kwargs.get('tokenize', True):
        gloss_tokens = tier_tokens(glosses(inst))
    else:
        gloss_tokens = tier_tokens(gloss(inst))

    trans_tokens = tier_tokens(trans(inst))

    # Use POS tags from the classifier if available.
    if kwargs.get('use_pos', False):
        gloss_pos_tier = pos_tag_tier(inst, gloss(inst).id, tag_method=INTENT_POS_CLASS)
        trans_pos_tier = pos_tag_tier(inst, trans(inst).id, tag_method=INTENT_POS_TAGGER)

        if gloss_pos_tier is None:
            ALIGN_LOG.warn(ARG_ALN_HEURPOS + ' alignment requested, but gloss tags were not available. Skipping for instance {}.'.format(inst.id))
        if trans_pos_tier is None:
            ALIGN_LOG.warn(ARG_ALN_HEURPOS + ' alignment requested, but trans-tagger tags were not available. Skipping for instance "{}"'.format(inst.id))

        if not (gloss_pos_tier is None or trans_pos_tier is None):
            # TODO: In order to do the alignment with POS tags, they need to be at the morpheme level. Find a better way to do this?
            # Make sure to expand the POS tags to function at the morpheme-level...
            if kwargs.get('tokenize', True):
                glosses_tags = [gloss_pos_tier[item_index(find_gloss_word(inst, gloss))-1] for gloss in glosses(inst)]
                kwargs['gloss_pos'] = glosses_tags
            else:
                kwargs['gloss_pos'] = gloss_pos_tier

            kwargs['trans_pos'] = trans_pos_tier

    aln = heur_alignments(gloss_tokens, trans_tokens, **kwargs).flip()

    # -------------------------------------------
    # Set the appropriate method, based on whether
    # -------------------------------------------
    if kwargs.get('use_pos'):
        aln_method = INTENT_ALN_HEURPOS
    else:
        aln_method = INTENT_ALN_HEUR

    # -------------------------------------------
    # Now, add these alignments as bilingual alignments...
    # -------------------------------------------
    if kwargs.get('tokenize', True):
        set_bilingual_alignment(inst, trans(inst), glosses(inst), aln, aln_method=aln_method)
    else:
        set_bilingual_alignment(inst, trans(inst), glosses(inst), aln, aln_method=aln_method)

    return get_trans_gloss_alignment(inst, aln_method=aln_method)

def giza_align_l_t(inst, symmetric = None):
    """
    Perform giza alignments directly from language to translation lines, for comparison

    :rtype: Alignment
    """

    l_sents = [tier_text(lang(i), return_list=True) for i in inst]
    t_sents = [tier_text(trans(i), return_list=True) for i in inst]

    ga = GizaAligner()

    t_l_sents = ga.temp_train(t_sents, l_sents)

    assert len(t_l_sents) == len(inst)

    if symmetric is not None:
        l_t_sents = ga.temp_train(l_sents, t_sents)


    for i, igt in enumerate(inst):
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
        set_bilingual_alignment(igt, trans(igt), lang(igt), t_l, aln_method = INTENT_ALN_GIZA)



def giza_align_t_g(xc, aligner=ALIGNER_GIZA, resume = True, use_heur = False, symmetric = SYMMETRIC_INTERSECT):
    """
    Perform giza alignments on the gloss and translation
    lines.

    :param resume: Whether to "resume" from the saved aligner, or start fresh.
    :type resume: bool
    """
    import logging
    ALIGN_LOG = logging.getLogger("GIZA")

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

    sent_num = 0

    ALIGN_LOG.info("Building up parallel sentences for training...")
    for inst in xc:
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

                id_pairs[inst.id] = sent_num
                sent_num+=1

        except (NoNormLineException, MultipleNormLineException) as nnle:
            continue


    # Tack on the heuristically aligned g/t words
    # to the end of the sents, so they won't mess
    # up alignment.

    g_sents.extend(g_morphs)
    t_sents.extend(t_words)

    ALIGN_LOG.info("Beginning training...")
    if aligner == ALIGNER_FASTALIGN:
        ALIGN_LOG.info('Attempting to align corpus "{}" using fastalign'.format(xc.id))
        g_t_alignments = fast_align_sents(g_sents, t_sents)
        t_g_alignments = fast_align_sents(t_sents, g_sents)

    elif aligner == ALIGNER_GIZA:
        ALIGN_LOG.info('Attempting to align corpus "{}" with giza'.format(xc.id))

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
    if len(g_t_alignments) != sent_num:
        raise AlignmentError('Something went wrong with statistical alignment, {} alignments were returned, {} expected.'.format(len(g_t_alignments), sent_num))

    # -------------------------------------------
    # Next, iterate through the aligned sentences and assign their alignments
    # to the instance.
    # -------------------------------------------
    if use_heur:
        aln_method = INTENT_ALN_GIZAHEUR
    else:
        aln_method = INTENT_ALN_GIZA

    for igt in xc:
        if igt.id in id_pairs:
            g_t_asent = g_t_alignments[id_pairs[igt.id]]
            t_g_aln = g_t_asent.flip()
            set_bilingual_alignment(igt, trans(igt), glosses(igt), t_g_aln, aln_method = aln_method)

def project_pt_tier(inst, proj_aln_method=None):
    """

    :raise PhraseStructureProjectionException: If there is no translation parse already in the tree, raise this error.
    """
    trans_parse_tier = get_trans_parse_tier(inst)

    if trans_parse_tier is None:
        raise PhraseStructureProjectionException('Translation parse not found for instance "%s"' % inst.id)

    trans_tree = read_pt(trans_parse_tier)

    # This might raise a ProjectionTransGlossException if the trans and gloss
    # alignments don't exist.
    tl_aln = get_trans_gloss_lang_alignment(inst, aln_method=proj_aln_method)

    # Do the actual tree projection and create a tree object
    proj_tree = project_ps(trans_tree, lang(inst), tl_aln)

    # Now, create a tier from that tree object.
    create_pt_tier(inst, proj_tree, lang(inst),
                   parse_method=INTENT_PS_PROJ,
                   source_tier=get_trans_parse_tier(inst),
                   aln_type=tl_aln.type)

def project_ds_tier(inst, proj_aln_method=None):
    """
    Project the dependency structure found in this tree.
    """

    # If a tier previously existed, overwrite it...
    old_lang_ds_tier = get_ds_tier(inst, lang(inst))
    if old_lang_ds_tier is not None:
        delete_tier(old_lang_ds_tier)

    # Get the trans DS, if it exists.
    src_t = get_trans_ds(inst)
    if src_t is None:
        raise ProjectionException('No dependency tree found for igt "{}"'.format(inst.id))
    else:
        tgt_w = lang(inst)
        aln = get_trans_gloss_lang_alignment(inst, aln_method=proj_aln_method)

        trans_ds_tier = get_ds_tier(inst, trans(inst))
        proj_t = project_ds(src_t, tgt_w, aln)

        create_dt_tier(inst, proj_t, lang(inst), parse_method=INTENT_DS_PROJ, source_tier=trans_ds_tier, aln_type=aln.type)

# =============================================================================
# POS TAG STUFF
# =============================================================================
def project_trans_pos_to_gloss(inst, aln_method=None, trans_tag_method=None):
    """
    Project POS tags from the translation words to the gloss words.

    :param trans_tag_method: POS tag method to use in searching for the translation POS tags.
    :param aln_method: Alignment method to use in projecting from trans to gloss.
    """

    # Remove previous gloss tags created by us if specified...
    attributes = {ALIGNMENT:gloss(inst).id}

    # Remove the previous gloss tags if they are present...
    prev_t = pos_tag_tier(inst, gloss(inst).id, tag_method=INTENT_POS_PROJ)
    if prev_t is not None:
        delete_tier(prev_t)

    # Get the trans tags...
    trans_tags = pos_tag_tier(inst, trans(inst).id, tag_method=trans_tag_method)

    # If we don't get any trans tags back, throw an exception:
    if not trans_tags:
        project_creator_except("There were no translation-line POS tags found",
                               "Please create the appropriate translation-line POS tags before projecting.",
                               INTENT_POS_PROJ)

    t_g_aln = get_trans_gloss_alignment(inst, aln_method=aln_method)


    # Create the new pos tier.
    # TODO: There should be a more unified approach to transferring tags.

    pt = Tier(type=POS_TIER_TYPE,
              id=gen_tier_id(inst, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=gloss(inst).id),
              alignment=gloss(inst).id, attributes=attributes)

    # Add the metadata about this tier...
    set_intent_method(pt, INTENT_POS_PROJ)
    set_intent_proj_data(pt, trans_tags, t_g_aln.type)


    for t_i, g_i in sorted(t_g_aln):
        g_word = gloss(inst)[g_i - 1]
        t_tag = trans_tags[t_i-1]

        # Order of precedence:
        # NOUN > VERB > ADJ > ADV > PRON > DET > ADP > CONJ > PRT > NUM > PUNC > X
        precedence = ['NOUN','VERB', 'ADJ', 'ADV', 'PRON', 'DET', 'ADP', 'CONJ', 'PRT', 'NUM', 'PUNC', 'X']

        # Look for a tag that aligns with the given word.
        g_tag = xigt_find(pt, alignment=g_word.id)

        # If it isn't already specified, go ahead and insert it.
        if g_tag is None:
            pt.append(Item(id=ask_item_id(pt), alignment=g_word.id, text=t_tag.value()))

        # If it has been specified, see if it has higher precedence than the tag
        # that already exists and replace it if it does.
        elif g_tag.value() in precedence and t_tag.value() in precedence:
            old_index = precedence.index(g_tag.value())
            new_index = precedence.index(t_tag.value())
            if new_index < old_index:
                g_tag.text = t_tag.value()


    inst.append(pt)


def project_lang_to_gloss(inst, tagmap=None):
    """
    This function serves the purpose of transferring language-line POS tags to the gloss line
     (needed with the CTN data, for instance).

    :type tagmap: TagMap
    :param tag_method:
    """

    lang_pos_tags = lang_tag_tier(inst)
    if not lang_pos_tags:
        project_creator_except("No lang-line POS tags found.", None, None)

    # Get the lang-gloss alignment...
    alignment = tier_alignment(gloss(inst))

    # Retrieve the tagset mapping.
    if tagmap:
        tm = TagMap(tagmap)

    # Create the POS tier
    new_id = gen_tier_id(inst, POS_TIER_ID, alignment=gloss(inst).id)
    pt = Tier(type=POS_TIER_TYPE, id=new_id, alignment=gloss(inst).id)

    # And add the metadata for the source (intent) and tagging method
    set_intent_method(pt, INTENT_POS_MANUAL)

    for lang_tag in lang_pos_tags:
        # Get the gloss word related to this tag. It should share
        # an alignment with the lang_tag...
        gloss_word = xigt_find(inst, alignment=lang_tag.alignment,
                               # And it's parent tier should be the GLOSS_WORD_TYPE.
                                 others=[lambda x: hasattr(x, 'tier') and x.tier.type == GLOSS_WORD_TYPE])

        # Do the tag mapping...
        if tagmap:
            postag = tm.get(lang_tag.value())
        else:
            postag = lang_tag.value()


        gpos = Item(id=pt.askItemId(), alignment = gloss_word.id, text=postag)
        pt.append(gpos)

    inst.append(pt)

def handle_unknown_pos(inst, token, handling_method=None, classifier=None):
    token_index = item_index(token)
    pos = UNKNOWN_TAG
    if re.match(punc_re_mult, token.value(), flags=re.U):
        pos = PUNC_TAG
    elif handling_method == 'noun':
        pos = 'NOUN'
    elif handling_method in ['keep', None]:
        pass
    elif handling_method == 'classify':
        raise Exception("HANDLING METHOD NOT IMPLEMENTED.")
    return pos


def project_gloss_pos_to_lang(inst, tag_method = None, unk_handling=None, classifier=None, posdict=None):
    """
    Project POS tags from gloss words to language words. This assumes that we have
    alignment tags on the gloss words already that align them to the language words.
    """

    lang_tag_tier = pos_tag_tier(inst, lang(inst).id, tag_method=tag_method)
    if lang_tag_tier is not None:
        delete_tier(lang_tag_tier)

    gloss_tag_tier = pos_tag_tier(inst, gloss(inst).id, tag_method=tag_method)

    # If we don't have gloss tags by that creator...
    if not gloss_tag_tier:
        project_creator_except("There were no gloss-line POS tags found",
                                "Please create the appropriate gloss-line POS tags before projecting.",
                                tag_method)

    alignment = tier_alignment(gloss(inst))

    # If we don't have an alignment between language and gloss line,
    # throw an error.
    if not alignment:
        raise GlossLangAlignException()

    # Get the bilingual alignment from trans to
    # Create the new pos tier...
    pt = Tier(type=POS_TIER_TYPE,
              id=gen_tier_id(inst, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=lang(inst).id),
              alignment=lang(inst).id)

    # Add the metadata as to the source
    set_intent_method(pt, tag_method)
    set_intent_proj_data(pt, gloss_tag_tier, INTENT_ALN_1TO1)

    # -------------------------------------------
    # Iterate over the language line to find punctuation...
    # -------------------------------------------
    for l_idx, l_w in enumerate(lang(inst)):

        l_w_string = l_w.value()
        if re.match(punc_re_mult, l_w_string.strip(), flags=re.U):
            label = PUNC_TAG
        else:
            g_indices = alignment.tgt_to_src(l_idx+1)
            assert len(g_indices) <= 1, 'Number of gloss tokens aligned to for id: "{}-{}": {}'.format(inst.id, l_w.id, len(g_indices))
            g_idx = g_indices[0] - 1
            g_w = gloss(inst)[g_idx]
            # Find the tag associated with this word.
            g_tag = xigt_find(gloss_tag_tier, attributes={ALIGNMENT:g_w.id})

            # If no gloss tag exists for this...
            if g_tag is None:
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
                        kwargs['prev_gram'] = gloss(inst)[g_idx-1 - 1].value()
                    if g_idx < len(gloss(inst)):
                        kwargs['next_gram'] = gloss(inst)[g_idx-1 + 1].value()

                    # Replace the whitespace in the gloss word for error
                    # TODO: Another whitespace replacement handling.
                    g_content = re.sub('\s+','', g_w.value())


                    label = classifier.classify_string(g_content, **kwargs).largest()[0]

                else:
                    raise ProjectionException('Unknown unk_handling method "%s"' % unk_handling)

            else:
                label = g_tag.value()

        pt.append(Item(id=ask_item_id(pt), alignment = l_w.id, text=label))



    inst.append(pt)

# =============================================================================
# Tag Production
# =============================================================================
def tag_trans_pos(inst, tagger=None):
    """
    Run the stanford tagger on the translation words and return the POS tags.

    :param tagger: The active POS tagger model.
    :type tagger: StanfordPOSTagger
    """
    if tagger is None:
        tagger = StanfordPOSTagger(tagger_model)

    trans_tags = [i.label for i in tagger.tag(tier_text(trans(inst)))]

    # Add the generated pos tags to the tier.
    add_pos_tags(inst, trans(inst).id, trans_tags, tag_method=INTENT_POS_TAGGER)
    return trans_tags

def classify_gloss_pos(inst, classifier_obj=None, **kwargs):
    """
    Run the classifier on the gloss words and return the POS tags.

    :param classifier_obj: the active mallet classifier to classify this language line.
    :type classifier_obj: MalletMaxent
    """
    if classifier_obj is None:
        classifier_obj = MalletMaxent()

    attributes = {ALIGNMENT:gloss(inst).id}

    # Search for a previous run and remove if found...
    prev_tier = pos_tag_tier(inst, gloss(inst).id, tag_method = INTENT_POS_CLASS)

    if prev_tier:
        delete_tier(prev_tier)

    kwargs['prev_gram'] = None
    kwargs['next_gram'] = None

    tags = []

    # Iterate over the gloss tokens...
    for i, gloss_token in enumerate(tier_tokens(gloss(inst))):

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
            if i+1 < len(gloss(inst)):
                kwargs['next_gram'] = tier_tokens(gloss(inst))[i+1]
            if i-1 >= 0:
                kwargs['prev_gram'] = tier_tokens(gloss(inst))[i-1]

            # The classifier returns a Classification object which has all the weights...
            # obtain the highest weight.
            result = classifier_obj.classify_string(gloss_token, **kwargs)

            if len(result) == 0:
                best = ['UNK']
            else:
                best = result.largest()

            # Return the POS tags
            tags.append(best[0])

    add_pos_tags(inst, gloss(inst).id, tags, tag_method=INTENT_POS_CLASS)
    return tags

def parse_translation_line(inst, parser=None, pt=False, dt=False):
    """
    Parse the translation line in order to project phrase structure.

    :param parser: Initialized StanfordParser
    :type parser: StanfordParser
    """
    import logging
    PARSELOG = logging.getLogger('PARSER')

    if parser is None:
        parser = StanfordParser()

    assert pt or dt, "At least one of pt or dt should be true."

    PARSELOG.debug('Attempting to parse translation line of instance "{}"'.format(inst.id))

    # Replace any parens in the translation line with square brackets, since they
    # will cause problems in the parsing otherwise.

    trans_text = tier_text(trans(inst)).replace('(', '[')
    trans_text = trans_text.replace(')',']')

    result = parser.parse(trans_text)

    PARSELOG.debug('Result of translation parse: {}'.format(result.pt))

    if pt and result.pt:
        create_pt_tier(inst, result.pt, trans(inst), parse_method=INTENT_PS_PARSER)
    if dt and result.dt:
        create_dt_tier(inst, result.dt, trans(inst), parse_method=INTENT_DS_PARSER)

# -------------------------------------------
# Dependency
# -------------------------------------------
def read_ds(tier, pos_source=None, unk_pos_handling=None):
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
    pos_tier = pos_tag_tier(tier.igt, tier.attributes.get(DS_DEP_ATTRIBUTE), tag_method=pos_source)

    for item in tier:
        dep  = item.attributes.get(DS_DEP_ATTRIBUTE)
        head = item.attributes.get(DS_HEAD_ATTRIBUTE)

        # Get the POS tag if it exists
        pos = None
        if pos_tier:
            pos_item = xigt_find(pos_tier, alignment=dep)
            if pos_item:
                pos = pos_item.value()

        # Get the word value...
        dep_w = xigt_find(tier.igt, id=dep)
        dep_w_string = dep_w.value()
        dep_t = Terminal(dep_w_string, item_index(dep_w))

        # If the pos is "None" but it's clearly a punctuation tag...
        if pos_tier is not None and pos is None:
            handle_unknown_pos(tier.igt, dep_w, handling_method=unk_pos_handling)

        if head is not None:
            head_w = xigt_find(tier.igt, id=head)
            head_t = Terminal(head_w.value(), item_index(head_w))
        else:
            head_t = Terminal('ROOT', 0)

        e = DepEdge(head=head_t, dep=dep_t, type=item.value(), pos=pos)
        edges.append(e)

    dt = build_dep_edges(edges)
    return dt



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
    segment_ids = set(ids(morph.segmentation))
    assert len(segment_ids) == 1, "A morph should not segment more than one word"
    return xigt_find(inst, id=segment_ids.pop())


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



#===============================================================================
# • Finding References ---
#===============================================================================






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

    # First, let's discard all the punctuation from both lines.
    these_words = [w for w in this  if not re.match(punc_re+'+', w.value().strip())]
    those_words = [w for w in other if not re.match(punc_re+'+', w.value().strip())]

    if len(these_words) != len(those_words):
        raise GlossLangAlignException('Gloss and language lines could not be auto-aligned for igt "%s"' % this.igt.id)
    else:
        # Note on the tier the alignment
        this.alignment = other.id

        # Align the words 1-to-1, left-to-right
        for my_word, their_word in zip(these_words, those_words):
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
            word_item = xigt_find(tier.igt, id=aln)
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

def basic_processing(inst):
    # Create the clean tier
    """
    Finish the loading actions of an IGT instance. (Create the normal and
    clean tiers if they don't exist...)

    """
    generate_clean_tier(inst)
    generate_normal_tier(inst)

    # Create the word and phrase tiers...
    try:
        trans(inst)
    except XigtFormatException:
        pass

    try:
        gloss(inst)
    except XigtFormatException:
        pass

    try:
        haslang = lang(inst)
    except XigtFormatException:
        haslang = False

    # Create the morpheme tiers...
    try:
        hasgloss = glosses(inst)
    except (NoGlossLineException, EmptyGlossException):
        hasgloss = False

    try:
        morphemes(inst)
    except NoLangLineException:
        pass

    if hasgloss and haslang:
        add_gloss_lang_alignments(inst)


def add_gloss_lang_alignments(inst):
    # Finally, do morpheme-to-morpheme alignment between gloss
    # and language if it's not already done...
    if not glosses(inst).alignment:
        morph_align(glosses(inst), morphemes(inst))

    if not gloss(inst).alignment:
        word_align(gloss(inst), lang(inst))

def remove_alignments(self, aln_method=None):
    """
    Remove alignment information from all instances.
    """
    filters = []
    if aln_method is not None:
        filters = [lambda x: get_intent_method(x) == aln_method]

    for inst in self:
        for t in xigt_findall(inst, type=ALN_TIER_TYPE, others=filters):
            t.delete()

def copy_xigt(obj, **kwargs):
    if isinstance(obj, XigtCorpus):
        ret_obj = XigtCorpus(id=obj.id, type=obj.type, attributes=copy.copy(obj.attributes), metadata=copy.copy(obj.metadata), namespace=obj.namespace, nsmap=obj.nsmap)
        for inst in obj:
            ret_obj.append(copy_xigt(inst, corp=ret_obj))
    elif isinstance(obj, Igt):
        ret_obj = Igt(id=obj.id, type=obj.type, attributes=copy.copy(obj.attributes), metadata=copy.copy(obj.metadata), corpus=kwargs.get('corp'), namespace=obj.namespace, nsmap=obj.nsmap)
        for tier in obj:
            ret_obj.append(copy_xigt(tier, igt=ret_obj))

    elif isinstance(obj, Tier):
        ret_obj = Tier(id=obj.id, type=obj.type, alignment=obj.alignment, content=obj.content, segmentation=obj.segmentation, attributes=copy.copy(obj.attributes), metadata=copy.copy(obj.metadata), igt=kwargs.get('igt'), namespace=obj.namespace, nsmap=obj.nsmap)
        for item in obj:
            ret_obj.append(copy_xigt(item, tier=ret_obj))

    elif isinstance(obj, Item):
        ret_obj = Item(id=obj.id, type=obj.type, alignment=obj.alignment, content=obj.content, segmentation=obj.segmentation, attributes=copy.copy(obj.attributes), text=obj.text, tier=kwargs.get('tier'), namespace=obj.namespace, nsmap=obj.nsmap)
    else:
        raise XigtFormatException("Attempt to copy non-xigt object.")

    return ret_obj
# -------------------------------------------
# Imports

from .exceptions import *
from .igtutils import *
from .metadata import get_intent_method, get_word_level_info, set_intent_method, remove_word_level_info, \
    set_intent_proj_data
from intent.alignment.Alignment import Alignment, heur_alignments, AlignmentError
from intent.consts import *
