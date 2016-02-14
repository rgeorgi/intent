from argparse import ArgumentParser
from lxml import etree as ET

import re

from intent.trees import DepTree, Terminal
from intent.utils.token import POSToken


def strip_ns(e):
    def stripit(s):
        return re.sub(r'{.*}(.+)$', r'\1', s)
    e.tag = stripit(e.tag)
    for k in e.attrib.keys():
        new_k = stripit(k)
        e.attrib[new_k] = e.attrib[k]
    for elt in e:
        strip_ns(elt)

def find_ancestor(e):
    if e.tag in ['childnodes', 'LM'] and e.get('order'):
        return e
    else:
        return find_ancestor(e.getparent())

def assemble_ds(words, index_pairs, cur_head = -1, parent_node = None):

    # Get all the dependents
    dep_indices = [i[1] for i in index_pairs if i[0] == cur_head]
    if not dep_indices:
        return None
    else:
        if parent_node is None:
            parent_node = DepTree.root()

        for dep_index in dep_indices:
            word = words[dep_index-1]
            dt = DepTree(word.text, order=int(dep_index), pos=word.pos)
            parent_node.append(dt)
            assemble_ds(words, index_pairs, cur_head = dep_index, parent_node=dt)
            dt.sort(key=lambda x: x.word_index)

        return parent_node

class Word():
    def __init__(self, text, pos=None, order=-1, id=None, gloss=None):
        self.text = text
        self.pos = pos
        self.order = order
        self.gloss = gloss


def convert_pml_sent(sent):
    # Here we are at the root node...
    sentid = sent.get('id')

    pml_words = sent.findall(".//form")

    ds = DepTree('ROOT', [], order=0)
    words = []
    index_pairs = []

    # -------------------------------------------
    # Sort the words and re-number, because it looks like
    # sometimes the indices refer to things that have been deleted.
    # -------------------------------------------
    pml_words = sorted(pml_words, key=lambda x: int(x.getparent().get('order')))

    # -------------------------------------------
    # Make a list of all the words, and their attributes.
    # also, keep track o
    # -------------------------------------------
    indices_map = {}
    for idx, word in enumerate(pml_words):
        container = word.getparent()
        nodeid    = container.get('id')
        order     = int(container.get('order'))
        text      = word.text
        pos       = None if not container.find('pos') else container.find('pos').text
        parent    = find_ancestor(container.getparent())
        parentid  = parent.get('id')
        parentidx = int(parent.get('order'))
        gloss     = None if not container.find('gloss') else container.find('gloss').text

        w = Word(text, order=order, id=nodeid, pos=pos, gloss=gloss)
        words.append(w)
        index_pairs.append((parentidx, order))
        indices_map[order] = idx+1

    for i, pair in enumerate(index_pairs):
        head, child = pair
        head = indices_map[head] if head != -1 else -1
        child= indices_map[child]
        index_pairs[i] = (head, child)

    words = sorted(words, key=lambda x: x.order)


    dt = assemble_ds(words, index_pairs)
    print(dt)

def load_pml(path):
    t = ET.parse(path)
    root = t.getroot()
    ns = strip_ns(root)
    return root

def convert_pml(f_path, e_path, a_path, o_path):

    e_root = load_pml(f_path)
    sents = e_root.findall(".//LM[@order='-1']")
    for sent in sents:
        convert_pml_sent(sent)




if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('-f', help='Foreign language file.', required=True)
    p.add_argument('-e', help='English language file.', required=True)
    p.add_argument('-a', help='Alignment file.', required=True)
    p.add_argument('-o', help='Output XIGT file', required=True)

    args = p.parse_args()

    convert_pml(args.f, args.e, args.a, args.o)