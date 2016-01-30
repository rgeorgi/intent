import re
import string

from intent.consts import *
from intent.igt.exceptions import NoNormLineException, MultipleNormLineException, EmptyGlossException
from intent.igt.metadata import get_intent_method
from xigt import ref, Tier, Item, Igt
from xigt.ref import ids
from xigt.xigtpath import find, findall
from xigt.consts import SEGMENTATION, CONTENT, ALIGNMENT
from xigt.mixins import XigtContainerMixin

# -------------------------------------------
# FIND
# -------------------------------------------

def create_aln_expr(id, start=None, stop=None):
    """
    Create an alignment expression, such as ``n2[5:8]`` or ``tw1`` given an id, and start/stop range.

    :param id: ID with which to align
    :param start: Range at which to start
    :type start: int
    :param stop: Range at which to stop
    :type stop: int
    """

    if start is None and stop is None:
        return id
    elif start is not None and stop is not None:
        return '%s[%d:%d]' % (id, start, stop)
    else:
        raise Exception('Invalid alignment expression request')


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

def xigt_find(obj, **kwargs):
    found = _find_in_self(obj, _build_filterlist(**kwargs))
    if found is not None:
        return obj

    # If we are working on a container object, iterate
    # over its children.
    elif isinstance(obj, XigtContainerMixin):
        found = None
        for child in obj:
            found = xigt_find(child, **kwargs)
            if found is not None:
                break
        return found

def xigt_findall(obj, **kwargs):
    found = []
    found_item = _find_in_self(obj, _build_filterlist(**kwargs))
    if found_item is not None:
        found = [found_item]

    # If we are working on a container object, iterate over
    # the children.
    if isinstance(obj, XigtContainerMixin):
        for child in obj:
            found += xigt_findall(child, **kwargs)


    return found


# -------------------------------------------
# Some convenience methods for common searches
# -------------------------------------------
def text_tier(inst, state):
    return xigt_find(inst, type=ODIN_TYPE, attributes={STATE_ATTRIBUTE:state})

def raw_tier(inst) -> Tier:
    return text_tier(inst, RAW_STATE)

def cleaned_tier(inst) -> Tier:
    return text_tier(inst, CLEAN_STATE)

def normalized_tier(inst) -> Tier:
    return text_tier(inst, NORM_STATE)



# -------------------------------------------
# Retrieve Tiers
# -------------------------------------------
def item_index(item):
    """
    Retrieve the index of a given item on its parent tier.

    :type item: Item
    """
    return list(item.tier).index(item)+1

# -------------------------------------------
# GENERATING ID STRINGS
# -------------------------------------------
def gen_item_id(id_base, num):
    return '{}{}'.format(id_base, num+1)

def ask_item_id(tier):
    return gen_item_id(tier.id, len(tier))

def gen_tier_id(inst, id_base, tier_type=None, alignment=None, no_hyphenate=False):
    """
    Unified method to generate a tier ID string. (See: https://github.com/goodmami/xigt/wiki/Conventions)
    """

    # In order to number this item correctly, we need to decide how many tiers of the same type
    # there are. This is done by systematically adding filters to the list.
    filters = []

    # First, do we align with another item? (Either segmentation, alignment, or head/dep)
    if alignment is not None:
        filters.append(lambda x: aln_match(alignment)(x) or seg_match(alignment)(x) or ref_match(x, alignment, DS_HEAD_ATTRIBUTE))

    # Next, does the type match ours?
    if tier_type is not None:
        filters.append(type_match(tier_type))

    # Get the number of tiers that match this.
    if not filters:
        num_tiers = 0
    else:
        prev_tiers = xigt_findall(inst, others=filters)
        num_tiers = len(prev_tiers)


    id_str = id_base
    # Now, if we have specified the alignment, we also want to prepend
    # that to the generated id string.
    if alignment is not None:
        if no_hyphenate:
            return '{}{}'.format(alignment, id_str)
        else:
            id_str = '{}-{}'.format(alignment, id_str)

    # Finally, if we have multiple tiers of the same type that annotate the
    # same item, we should append a letter for the different analyses.
    if num_tiers > 0 and xigt_find(inst, id=id_str) is not None:
        while True:
            letters = string.ascii_lowercase
            assert num_tiers < 26, "More than 26 alternative analyses not currently supported"
            potential_id = id_str + '_{}'.format(letters[num_tiers])

            if xigt_find(inst, id=potential_id) is None:
                id_str = potential_id
                break
            else:
                num_tiers += 1

    return id_str


# -------------------------------------------
# FINDING ODIN TAGS
# -------------------------------------------


def odin_tags(obj):
    """
    Given an object, return the tags that it is ultimately aligned with.

    :param obj:
    """

    a = odin_ancestor(obj)
    if a:
        return a.attributes['tag'].split('+')
    else:
        return []


def odin_ancestor(obj):
    # ODIN_LOG.debug("Looking up the odin ancestor for {}".format(str(obj)))
    # If we are at an ODIN item, return.

    if isinstance(obj, Item) and obj.tier.type == ODIN_TYPE:
        return obj

    # An Igt instance can't have a tier ancestor.
    elif isinstance(obj, Igt):
        return None

    # Also, an ODIN tier can't get a specific item...
    elif isinstance(obj, Tier) and obj.type == ODIN_TYPE:
        return None

    else:


        if SEGMENTATION in obj.attributes:
            ref_attr = SEGMENTATION
        elif CONTENT in obj.attributes:
            ref_attr = CONTENT
        elif ALIGNMENT in obj.attributes:
            ref_attr = ALIGNMENT
        elif DS_DEP_ATTRIBUTE in obj.attributes:
            ref_attr = DS_DEP_ATTRIBUTE
        else:
            return None

        # If this item is a tier, we would like to follow a random object
        if isinstance(obj, Tier):
            if len(obj) == 0:
                id = obj.attributes[ref_attr]
            else:
                id = [ids(i.attributes[ref_attr])[0] for i in obj if ref_attr in i.attributes][0]
        elif isinstance(obj, Item):
            id = ids(obj.attributes[ref_attr])[0]
        else:
            raise Exception

        item = xigt_find(obj.igt, id=id)
        if item is None:
            return None
        else:
            return odin_ancestor(item)