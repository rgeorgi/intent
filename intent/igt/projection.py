from intent.consts import INTENT_PS_PROJ, INTENT_DS_PROJ, INTENT_POS_PROJ, POS_TIER_TYPE, POS_TIER_ID
from intent.igt.exceptions import PhraseStructureProjectionException, ProjectionException, project_creator_except
from intent.igt.metadata import set_intent_method
from intent.igt.metadata import set_intent_proj_data
from intent.igt.rgxigt import read_pt, gen_tier_id
from intent.igt.search import get_trans_parse_tier, get_trans_gloss_lang_alignment, lang, get_trans_gloss_alignment, \
    create_pt_tier, get_ds_tier, get_lang_ds, delete_tier, get_trans_ds, trans, create_dt_tier, gloss, get_pos_tags, \
    find_in_obj, ask_item_id
from intent.trees import project_ps, project_ds
from xigt import Tier, Item
from xigt.consts import ALIGNMENT


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
    tl_aln = get_trans_gloss_alignment(inst, aln_method=proj_aln_method)

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
    prev_t = get_pos_tags(inst, gloss(inst).id, tag_method=INTENT_POS_PROJ)
    if prev_t is not None:
        delete_tier(prev_t)

    # Get the trans tags...
    trans_tags = get_pos_tags(inst, trans(inst).id, tag_method=trans_tag_method)

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
        g_tag = find_in_obj(pt, alignment=g_word.id)

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