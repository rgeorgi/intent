import re

from intent.consts import *
from intent.igt.exceptions import PhraseStructureProjectionException, ProjectionException, project_creator_except, \
    GlossLangAlignException
from intent.igt.metadata import set_intent_method
from intent.igt.metadata import set_intent_proj_data
from intent.igt.rgxigt import read_pt, gen_tier_id
from intent.igt.search import get_trans_parse_tier, get_trans_gloss_lang_alignment, lang, get_trans_gloss_alignment, \
    create_pt_tier, get_ds_tier, get_lang_ds, delete_tier, get_trans_ds, trans, create_dt_tier, gloss, get_pos_tags, \
    find_in_obj, ask_item_id, get_aligned_tokens, tier_text, add_pos_tags, tier_tokens
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.trees import project_ps, project_ds
from intent.utils.env import classifier
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

def project_gloss_pos_to_lang(inst, tag_method = None, unk_handling=None, classifier=None, posdict=None):
    """
    Project POS tags from gloss words to language words. This assumes that we have
    alignment tags on the gloss words already that align them to the language words.
    """

    lang_tag_tier = get_pos_tags(inst, lang(inst).id, tag_method=tag_method)
    if lang_tag_tier is not None:
        delete_tier(lang_tag_tier)

    gloss_tag_tier = get_pos_tags(inst, gloss(inst).id, tag_method=tag_method)

    # If we don't have gloss tags by that creator...
    if not gloss_tag_tier:
        project_creator_except("There were no gloss-line POS tags found",
                                "Please create the appropriate gloss-line POS tags before projecting.",
                                tag_method)

    alignment = get_aligned_tokens(gloss(inst))

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

    for g_idx, l_idx in alignment:
        l_w = lang(inst)[l_idx - 1]
        g_w = gloss(inst)[g_idx - 1]

        # Find the tag associated with this word.
        g_tag = find_in_obj(gloss_tag_tier, attributes={ALIGNMENT:g_w.id})

        # If no gloss tag exists for this...
        if not g_tag:
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
def tag_trans_pos(inst, tagger):
    """
    Run the stanford tagger on the translation words and return the POS tags.

    :param tagger: The active POS tagger model.
    :type tagger: StanfordPOSTagger
    """

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
        classifier_obj = MalletMaxent(classifier)

    attributes = {ALIGNMENT:gloss(inst).id}

    # Search for a previous run and remove if found...
    prev_tier = get_pos_tags(inst, gloss(inst).id, tag_method = INTENT_POS_CLASS)

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

def parse_translation_line(inst, parser, pt=False, dt=False):
    """
    Parse the translation line in order to project phrase structure.

    :param parser: Initialized StanfordParser
    :type parser: StanfordParser
    """
    import logging
    PARSELOG = logging.getLogger('PARSER')

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