# -------------------------------------------
# FILTERS
# -------------------------------------------
import re

from intent.igt.consts import ODIN_TYPE, STATE_ATTRIBUTE, RAW_STATE, CLEAN_STATE, NORM_STATE
from xigt import ref
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

def raw_tier(inst):
    return text_tier(inst, RAW_STATE)

def cleaned_tier(inst):
    return text_tier(inst, CLEAN_STATE)

def normalized_tier(inst):
    return text_tier(inst, NORM_STATE)