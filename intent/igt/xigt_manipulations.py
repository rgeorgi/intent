from intent.igt.igtutils import strip_leading_whitespace
from intent.utils.dicts import DefaultOrderedDict
from xigt.consts import ALIGNMENT

# -------------------------------------------

def get_raw_tier(inst):
    """
    Retrieve the raw ODIN tier, otherwise raise an exception.
    """
    raw_tier = find_in_obj(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:RAW_STATE})

    if not raw_tier:
        raise NoODINRawException('No raw tier found.')
    else:
        return raw_tier

def get_normal_tier(inst, clean=True, generate=True):
    # If a normal tier already exists, return it.
    normal_tier = find_in_obj(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:NORM_STATE})
    if normal_tier is not None:
        normal_tier.__class__ = RGTier
        return normal_tier

    # Otherwise, create a new one, with only L, G and T lines.
    elif generate:
        normal_tier = RGLineTier(id = NORM_ID, type=ODIN_TYPE,
                                 attributes={STATE_ATTRIBUTE:NORM_STATE, ALIGNMENT:get_clean_tier(inst).id})

        # Get one item per...
        add_normal_line(inst, normal_tier, ODIN_LANG_TAG, clean_lang_string if clean else lambda x: x)
        add_normal_line(inst, normal_tier, ODIN_GLOSS_TAG, clean_gloss_string if clean else lambda x: x)
        add_normal_line(inst, normal_tier, ODIN_TRANS_TAG, clean_trans_string if clean else lambda x: x)

        # -------------------------------------------
        # Now, remove the whitespace shared between lines.
        # -------------------------------------------
        textlines = strip_leading_whitespace([i.text for i in normal_tier])
        for textline, item in zip(textlines, normal_tier):
            item.text = textline

        inst.append(normal_tier)
        return normal_tier

def get_clean_tier(inst, merge=False, generate=True):
    """
    If the clean odin tier exists, return it. Otherwise, create it.

    """

    # If a clean tier already exists, return it.
    clean_tier = find_in_obj(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:CLEAN_STATE})
    if clean_tier:
        return clean_tier

    elif generate:
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

            if len(lines) == 1:
                text = lines[0].value()
                new_tag = lines[0].attributes['tag']
                align_id = lines[0].id

            elif len(lines) > 1:
                PARSELOG.info('Corruption detected in instance %s: %s' % (inst.id, [l.attributes['tag'] for l in lines]))
                for l in lines:
                    PARSELOG.debug('BEFORE: %s' % l)

                text = merge_lines([l.value() for l in lines])
                PARSELOG.debug('AFTER: %s' % text)
                new_tag = primary_tag
                align_id = ','.join([l.id for l in lines])

            item = RGLine(id=clean_tier.askItemId(), alignment=align_id, text=text,
                          attributes={'tag': new_tag})
            clean_tier.add(item)

        inst.append(clean_tier)
        return clean_tier

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
    logging.log(1000, rgencode(inst))

    # -------------------------------------------
    # If we are providing new clean lines, remove
    # the old ones.
    # -------------------------------------------
    if clean_lines:
        old_clean_tier = get_clean_tier(inst, generate=False)
        if old_clean_tier is not None:
            inst.remove(old_clean_tier)

    # -------------------------------------------
    # If we are providing new norm lines, remove
    # the old ones.
    # -------------------------------------------
    if norm_lines:
        old_norm_tier = get_normal_tier(inst, generate=False)
        if old_norm_tier is not None:
            inst.remove(old_norm_tier)

    # -------------------------------------------
    # At this point, we should only have the raw tier left.
    # -------------------------------------------
    if len(inst) > 1:
        logging.log(1000, rgencode(inst))
        raise Exception("Attempt to replace tiers on IGT with additional data")

    # -------------------------------------------
    # Create and append the clean/norm tiers
    # -------------------------------------------
    if clean_lines:
        new_clean_tier = create_text_tier_from_lines(inst, clean_lines, CLEAN_ID, CLEAN_STATE)
        inst.append(new_clean_tier)
    if norm_lines:
        new_norm_tier = create_text_tier_from_lines(inst, norm_lines, NORM_ID, NORM_STATE)
        inst.append(new_norm_tier)

    return inst



from .search import find_in_obj
from .consts import *
from .igtutils import merge_lines, clean_lang_string, clean_gloss_string, clean_trans_string
from .rgxigt import RGLineTier, PARSELOG, RGLine, RGTier, NoODINRawException
from .creation import *