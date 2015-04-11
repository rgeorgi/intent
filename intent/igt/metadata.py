"""
Created on Apr 9, 2015

:author: rgeorgi
"""
from xigt.metadata import Metadata, Meta
from intent.igt.consts import XIGT_META_TYPE
from xigt.mixins import XigtContainerMixin


def add_meta(obj, meta_type, val, metadata_type=XIGT_META_TYPE):
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
        m = obj.metadata
        if m:
            for metadata in obj.metadata:
                # If we have found the correct metadata
                # container, set that to the m to be
                # appended to.
                if metadata.type == metadata_type:
                    m = metadata
                    break

        # If there is no metadata, or the metadata
        # of the specified meta_type was not found, create it.
        if not m:
            m = Metadata(type=metadata_type)
            obj.metadata = m

        # Finally, add our Meta object to the metadata.
        m.append(Meta(type=meta_type,text=val))



def find_meta(obj, meta_type):
    """
    Given an object, search to find the text value of a Meta item
      with the given type ``type``.

    :param obj: Object to search for metadata on
    :param meta_type:
    :return:
    """
    if not isinstance(obj, XigtContainerMixin):
        return None
    if obj.metadata is not None:
        for metadata in obj.metadata:
            for meta in metadata.metas:
                if meta.type == meta_type:
                    return meta.text


