"""
Created on Apr 9, 2015

:author: rgeorgi
"""
from xigt.metadata import Metadata, Meta
from intent.igt.consts import XIGT_META_TYPE, XIGT_DATA_DATE, INTENT_META_SOURCE, XIGT_DATA_SRC, XIGT_DATA_PROV, \
    XIGT_DATA_METH, XIGT_DATA_FROM
from xigt.mixins import XigtContainerMixin
from datetime import datetime

def get_intent_method(obj):
    """
    Return the intent method used to generate the given object, or
    None if the method is not specified.

    :param obj: Object on which to look for the metadata
    :return: str or None
    """
    m = find_meta(obj, XIGT_DATA_PROV)
    if m is not None and m.attributes.get(XIGT_DATA_SRC) == INTENT_META_SOURCE:
        return m.attributes.get(XIGT_DATA_METH)

def set_intent_method(obj, method):
    """
    Set the data provenance attributes of the metadata to show that
    they were sourced from intent, using the specified method method.

    :param obj: Object to add metadata to.
    :param method: Method to set as the method attribute on the meta item.
    """
    add_meta(obj, XIGT_DATA_PROV, XIGT_DATA_SRC, INTENT_META_SOURCE)
    add_meta(obj, XIGT_DATA_PROV, XIGT_DATA_METH, method)


def set_intent_proj_data(obj, source_tier):
    """
    Using the source_tier tier, add some metadata to this instance to describe the source_tier
    that created the projection material.

    :param obj:
    :param source_tier:
    """
    add_meta(obj, XIGT_DATA_PROV, XIGT_DATA_FROM, source_tier.id)
    #add_meta(obj, XIGT_DATA_PROV, XIGT_DATA_ALNF, aln_tier.id)


def add_meta(obj, meta_type, attr, val, metadata_type=XIGT_META_TYPE, timestamp=True):
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
        metadata_list = obj.metadata
        md = None
        if metadata_list:
            for metadata in metadata_list:
                # If we have found the correct metadata
                # container, set that to the m to be
                # appended to.
                if metadata.type == metadata_type:
                    md = metadata
                    break

        # If there is no metadata, or the metadata
        # of the specified meta_type was not found, create it.
        if md is None:
            md = Metadata(type=metadata_type)
            obj.metadata = [md]

        # Finally, add our Meta object to the metadata.
        m = find_meta(obj, meta_type)
        if m is not None:
            m.attributes[attr] = val
        else:
            m = Meta(type=meta_type,attributes={attr:val})
            timestamp_meta(m)
            md.append(m)


def del_meta(obj, meta_type):
    """
    Remove the specified Meta type.

    :param obj:
    :param meta_type:
    """
    m = find_meta(obj, meta_type)
    if m is not None:
        md = m._parent
        md.remove(m)

        if not is_contentful_metadata(md):
            obj.metadata.remove(md)


def del_meta_attr(obj, meta_type, attr):
    """
    Remove the specified meta attribute

    :param obj:
    :param meta_type:
    :param attr:
    """
    # Find the Meta object
    m = find_meta(obj, meta_type)
    if m is not None:
        # If it has the specified attribute,
        # remove it.
        if attr in m.attributes:
            del m.attributes[attr]

        # If the Meta object has no text elements
        # or other contentful attributes (not timestamp)
        # Remove it from its parent.
        if not is_contentful_meta(m):
            del_meta(obj, meta_type)

def is_contentful_metadata(md):
    return len(md) > 0

def is_contentful_meta(m):
    has_text = m.text is not None
    # Also, the attributes should be more than just the timestamp
    # (i.e. the timestamp set should be a proper subset of all attributes)
    keys = [k for k in m.attributes.keys() if k != XIGT_DATA_DATE]
    return has_text or keys


def timestamp_meta(m):
    m.attributes[XIGT_DATA_DATE] = datetime.utcnow().replace(microsecond=0).isoformat()

def get_meta_timestamp(m):
    return m.attributes.get(XIGT_DATA_DATE)


def find_meta(obj, meta_type):
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
        for metadata in obj.metadata:
            for meta in metadata.metas:
                if meta.type == meta_type:
                    return meta

def find_meta_attr(obj, meta_type, attr):
    """
    Find the specific value of a metadata attribute, or None
    if the meta item does not exist, or does not have the
    specified attribute.

    :param obj:
    :param meta_type:
    :param attr:
    :return: str or None
    """
    m = find_meta(obj, meta_type)
    if m is not None:
        return m.attributes.get(attr)
    else:
        return None


