from intent.igt.exceptions import XigtFormatException
from intent.igt.references import find_in_obj, gen_item_id, create_aln_expr, ask_item_id, aligned_tags
from intent.consts import ODIN_TYPE, STATE_ATTRIBUTE, NORM_STATE, NORM_ID, ODIN_LANG_TAG, ODIN_GLOSS_TAG, ODIN_TRANS_TAG, \
    ODIN_TAG_ATTRIBUTE, TRANS_WORD_ID, TRANS_WORD_TYPE, ODIN_JUDGMENT_ATTRIBUTE, LANG_PHRASE_ID, LANG_PHRASE_TYPE
from intent.igt.igtutils import clean_trans_string, clean_gloss_string, clean_lang_string, strip_leading_whitespace, \
    rgencode
from intent.utils.token import sentence_tokenizer, tokenize_item
from xigt import Tier, Item
from xigt.consts import ALIGNMENT, SEGMENTATION


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
                  attributes={aln_attribute:create_aln_expr(cur_item.id, w.start, w.stop)}, tier=wt, start=w.start, stop=w.stop)
        wt.append(rw)

    return wt

def retrieve_phrase_tier(inst, tag, id, type):
    """
    Retrieve a phrase for the given tag, with the provided id and type.

    """

    # TODO FIXME: VERY kludgy and unstable...
    f = lambda x: tag in aligned_tags(x)
    pt = find_in_obj(inst, type=type, others=[f])

    if pt is None:
        n = get_normal_tier(inst)
        # Get the normalized line
        l = retrieve_normal_line(inst, tag)

        # -------------------------------------------
        # Create the phrase tier, and add a single phrase item.
        pt = Tier(id=id, type=type, content=n.id)

        # -------------------------------------------
        # Propagate the judgment attribute on the line to the phrase item
        phrase_attributes = {}
        old_judgment = l.attributes.get(ODIN_JUDGMENT_ATTRIBUTE)
        if l.attributes.get(ODIN_JUDGMENT_ATTRIBUTE) is not None:
            phrase_attributes[ODIN_JUDGMENT_ATTRIBUTE] = old_judgment

        pt.append(Tier(id=ask_item_id(pt), content=l.id, attributes=phrase_attributes))
        inst.append(pt)


    return pt

def retrieve_lang_phrase_tier(inst):
    """
    Retrieve the language phrase if it exists, otherwise create it.

    :param inst: Instance to search
    :type inst: RGIgt
    """
    return retrieve_phrase_tier(inst, ODIN_LANG_TAG, LANG_PHRASE_ID, LANG_PHRASE_TYPE)


# -------------------------------------------



def retrieve_trans_phrase(inst):
    """
    Retrieve the translation phrase tier if it exists, otherwise create it. (Making
    sure to align it with the language phrase if it is present)

    :param inst: Instance to search
    :type inst: RGIgt
    """
    tpt = retrieve_phrase_tier(inst, ODIN_TRANS_TAG, TRANS_PHRASE_ID, TRANS_PHRASE_TYPE)

    # Add the alignment with the language line phrase if it's not already there.
    if ALIGNMENT not in tpt.attributes:
        try:
            lpt = retrieve_lang_phrase_tier(inst)
            tpt.attributes[ALIGNMENT] = lpt.id
            tpt[0].attributes[ALIGNMENT] = lpt[0].id
        except MultipleNormLineException as mnle:
            pass
        except NoNormLineException as nlle:
            pass

    return tpt

def retrieve_trans_words(inst, create=True):
    """
    Retrieve the translation words tier from an instance.

    :type inst: RGIgt
    :rtype: RGWordTier
    """

    # Get the translation phrase tier
    tpt = retrieve_trans_phrase(inst)

    # Get the translation word tier
    twt = find_in_obj(inst,
                type=TRANS_WORD_TYPE,
                segmentation=tpt.id)

    if twt is None and create:
        twt = create_words_tier(tpt[0], TRANS_WORD_ID, TRANS_WORD_TYPE, tokenizer=sentence_tokenizer)
        inst.append(twt)

    return twt

def retrieve_lang_words(inst, create=True):
    """
    Retrieve the language words tier from an instance

    :type inst: RGIgt
    :rtype: RGWordTier
    """
    # Get the lang phrase tier
    lpt = retrieve_lang_phrase_tier(inst)

    # Get the lang word tier
    lwt = find_in_obj(inst, type=LANG_WORD_TYPE, segmentation=lpt.id)

    if lwt is None and create:
        lwt = create_words_tier(lpt[0], LANG_WORD_ID, LANG_WORD_TYPE)
        inst.append(lwt)

    return lwt


# -------------------------------------------
#
# -------------------------------------------

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

def add_normal_line_to_tier(inst, tier, tag, func):
    clean_tier = get_clean_tier(inst)
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