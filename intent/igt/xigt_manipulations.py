import re

from intent.igt.search import find_in_obj
from xigt import ref

from intent.igt.consts import ODIN_TYPE, STATE_ATTRIBUTE, CLEAN_STATE, CLEAN_ID, NORM_STATE, NORM_ID, ODIN_LANG_TAG, \
    ODIN_TRANS_TAG, ODIN_GLOSS_TAG
from intent.igt.igtutils import merge_lines, clean_lang_string, clean_gloss_string, clean_trans_string
from intent.igt.rgxigt import RGLineTier, PARSELOG, RGLine, RGTier
from intent.utils.dicts import DefaultOrderedDict
from xigt.consts import ALIGNMENT, SEGMENTATION, CONTENT




# -------------------------------------------


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
            inst.add_normal_line(normal_tier, ODIN_LANG_TAG, clean_lang_string if clean else lambda x: x)
            inst.add_normal_line(normal_tier, ODIN_GLOSS_TAG, clean_gloss_string if clean else lambda x: x)
            inst.add_normal_line(normal_tier, ODIN_TRANS_TAG, clean_trans_string if clean else lambda x: x)

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
        raw_tier = inst.raw_tier()


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

