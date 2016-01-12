"""
Created on Apr 9, 2015

:author: rgeorgi
"""
import xigt.xigtpath as xp
from xigt.metadata import Metadata, Meta
from intent.igt.consts import DATA_DATE, INTENT_META_SOURCE, DATA_SRC, DATA_PROV, \
    DATA_METH, DATA_FROM, INTENT_META_TYPE
from xigt.mixins import XigtContainerMixin
from datetime import datetime

def get_intent_method(obj):
    """
    Return the intent method used to generate the given object, or
    None if the method is not specified.

    :param obj: Object on which to look for the metadata
    :return: str or None
    """
    m = find_meta(obj, DATA_PROV)
    if m is not None and m.attributes.get(DATA_SRC) == INTENT_META_SOURCE:
        return m.attributes.get(DATA_METH)

def set_intent_method(obj, method):
    """
    Set the data provenance attributes of the metadata to show that
    they were sourced from intent, using the specified method method.

    :param obj: Object to add metadata to.
    :param method: Method to set as the method attribute on the meta item.
    """
    set_meta_attr(obj, DATA_PROV, DATA_SRC, INTENT_META_SOURCE)
    set_meta_attr(obj, DATA_PROV, DATA_METH, method)


def set_intent_proj_data(obj, source_tier):
    """
    Using the source_tier tier, add some metadata to this instance to describe the source_tier
    that created the projection material.

    :param obj:
    :param source_tier:
    """
    set_meta_attr(obj, DATA_PROV, DATA_FROM, source_tier.id)

def find_metadata(obj, metadata_type):
    found = None
    for md in obj.metadata:
        if md.type == metadata_type:
            found = md
            break
    return found


def set_meta(obj, m, metadata_type=INTENT_META_TYPE, timestamp=True):
    md = find_metadata(obj, metadata_type)

    # Add a new metadata container to the current object if
    # the type that we're looking for is not found.
    if md is None:
        md = Metadata(type=metadata_type)
        obj.metadata.append(md)

    replaced = False
    for i, meta in enumerate(md):
        if meta.type == m.type:
            md[i] = m
            break

    if not replaced:
        md.append(m)

def set_meta_text(obj, meta_type, text, metadata_type=INTENT_META_TYPE, timestamp=True):
    if not isinstance(obj, XigtContainerMixin):
        raise Exception("Attempt to add meta object on object ({}) that cannot contain meta".format(meta_type(obj)))
    else:
        m = find_meta(obj, meta_type, metadata_type=metadata_type)
        if m is None:
            m = Meta(type=meta_type, text=text)
            set_meta(obj, m, metadata_type=metadata_type, timestamp=timestamp)
        else:
            m.text = text
        timestamp_meta(m)

def set_meta_attr(obj, meta_type, attr, val, metadata_type=INTENT_META_TYPE, timestamp=True):
    """
    Add an arbitrary piece of metadata to a XIGT object that accepts metadata

    :param obj: XIGT object to add a piece of metadata to.
    :meta_type obj: XigtContainerMixin
    :param meta_type: Type of the Meta object to add
    :param val: Text value for the meta object to be added.
    :param metadata_type: Type for the metadata container in which to append the item.
    :raise Exception: If ``obj`` is of a meta_type that does not contain metadata.
    """
    if not isinstance(obj, XigtContainerMixin):
        raise Exception('Attempt to add meta object on object ({}) that cannot contain meta'.format(meta_type(obj)))
    else:
        m = find_meta(obj, meta_type, metadata_type=metadata_type)
        if m is None:
            m = Meta(type=meta_type, attributes={attr:val})
            set_meta(obj, m, metadata_type=metadata_type, timestamp=timestamp)
        else:
            m.attributes[attr] = val
        timestamp_meta(m)


def del_meta(obj, meta_type, metadata_type=None):
    """
    Remove the specified Meta type.

    :param obj:
    :param meta_type:
    """
    m = find_meta(obj, meta_type, metadata_type=metadata_type)
    if m is not None:
        md = m._parent
        md.remove(m)

        if not is_contentful_metadata(md):
            obj.metadata.remove(md)


def del_meta_attr(obj, meta_type, attr, metadata_type=None):
    """
    Remove the specified meta attribute

    :param obj:
    :param meta_type:
    :param attr:
    """
    # Find the Meta object
    m = find_meta(obj, meta_type, metadata_type=metadata_type)
    if m is not None:
        # If it has the specified attribute,
        # remove it.
        if attr in m.attributes:
            del m.attributes[attr]

        # If the Meta object has no text elements
        # or other contentful attributes (not timestamp)
        # Remove it from its parent.
        if not is_contentful_meta(m):
            del_meta(obj, meta_type, metadata_type=metadata_type)

def is_contentful_metadata(md):
    return len(md) > 0

def is_contentful_meta(m):
    has_text = m.text is not None
    # Also, the attributes should be more than just the timestamp
    # (i.e. the timestamp set should be a proper subset of all attributes)
    keys = [k for k in m.attributes.keys() if k != DATA_DATE]
    return has_text or keys


def timestamp_meta(m):
    m.attributes[DATA_DATE] = datetime.utcnow().replace(microsecond=0).isoformat()

def get_meta_timestamp(m):
    return m.attributes.get(DATA_DATE)


def find_meta(obj, meta_type, metadata_type = INTENT_META_TYPE):
    """
    Given an object, search to find the text value of a Meta item
      with the given type ``type``.

    :param obj: Object to search for metadata on
    :param meta_type:
    :return:
    :rtype: Meta
    """

    if not isinstance(obj, XigtContainerMixin):
        return None
    elif obj.metadata is not None:
        for metadata in [m for m in obj.metadata if m.type == metadata_type or metadata_type is None]:
            for meta in metadata.metas:
                if meta.type == meta_type:
                    return meta

def find_meta_attr(obj, meta_type, attr, metadata_type = INTENT_META_TYPE):
    """
    Find the specific value of a metadata attribute, or None
    if the meta item does not exist, or does not have the
    specified attribute.

    :param obj:
    :param meta_type:
    :param attr:
    :return: str or None
    """
    m = find_meta(obj, meta_type, metadata_type=metadata_type)
    if m is not None:
        return m.attributes.get(attr)
    else:
        return None

def set_meta_text(obj, meta_type, text, metadata_type=INTENT_META_TYPE):
    m = find_meta(obj, meta_type)
    if m is not None:
        m.text = text
    else:
        m = Meta(type=meta_type, text=text)
        set_meta(obj, m, metadata_type=metadata_type)


def find_meta_text(obj, meta_type):
    m = find_meta(obj, meta_type)
    if m is not None:
        return m.text