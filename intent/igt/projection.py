from intent.consts import INTENT_PS_PROJ, INTENT_DS_PROJ
from intent.igt.exceptions import PhraseStructureProjectionException, ProjectionException
from intent.igt.rgxigt import read_pt
from intent.igt.search import get_trans_parse_tier, get_trans_gloss_lang_alignment, lang, get_trans_gloss_alignment, \
    create_pt_tier, get_ds_tier, get_lang_ds, delete_tier, get_trans_ds, trans, create_dt_tier
from intent.trees import project_ps, project_ds


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