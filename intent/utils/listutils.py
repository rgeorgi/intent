'''
Created on Oct 23, 2013

@author: rgeorgi
'''
from unittest import TestCase


def all_indices(item, seq):
    matches = []
    for i in range(len(seq)):
        if item == seq[i]:
            matches.append(i)
    return matches

def uniqify (seq, idfun=None): 
    # order preserving
    """
    Given a sequence, return a sequence that
    contains only the unique items (while preserving
    the order).

    :param seq: Sequence to uniqify
    :param idfun: Function to apply to the instances to determine whether they are "unique"
    :return: list
    """
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        # in old Python versions:
        # if seen.has_key(marker)
        # but in new ones:
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result

def flatten_list(obj):
    """
    Given a set of embedded lists, return a single, "flattened" list.

    :param obj:
    :return:
    """
    if not isinstance(obj, list):
        return [obj]
    else:
        ret_list = []
        for elt in obj:
            ret_list.extend(flatten_list(elt))
        return ret_list

class FlattenTest(TestCase):

    def test_flatten(self):
        a = [[1,2],[[3,[4,5]]]]
        b = flatten_list(a)
        c = [1,2,3,4,5]
        d = flatten_list(c)

        self.assertEqual(b,c)
        self.assertEqual(c,d)