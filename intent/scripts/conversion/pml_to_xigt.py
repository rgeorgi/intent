import os
from argparse import ArgumentParser

import sys
from lxml import etree as ET

import re

from intent.alignment.Alignment import Alignment
from intent.consts import ODIN_TYPE, STATE_ATTRIBUTE, NORM_STATE, NORM_ID, ODIN_TAG_ATTRIBUTE, ODIN_LANG_TAG, \
    ODIN_GLOSS_TAG, ODIN_TRANS_TAG, LANG_WORD_ID, LANG_WORD_TYPE, LANG_PHRASE_TYPE, LANG_PHRASE_ID, TRANS_PHRASE_ID, \
    TRANS_PHRASE_TYPE, GLOSS_WORD_ID, GLOSS_WORD_TYPE, POS_TIER_ID, POS_TIER_TYPE, INTENT_DS_PARSER, INTENT_DS_MANUAL, \
    TRANS_WORD_ID, TRANS_WORD_TYPE, INTENT_POS_MANUAL, INTENT_ALN_MANUAL
from intent.igt.create_tiers import lang, gloss, generate_phrase_tier, generate_lang_phrase_tier, \
    generate_trans_phrase_tier, lang_phrase, create_word_tier, trans_phrase, trans
from intent.igt.igt_functions import create_dt_tier, add_pos_tags, word_align, set_bilingual_alignment, \
    get_bilingual_alignment
from intent.igt.igtutils import rgp
from intent.igt.references import ask_item_id, gen_tier_id
from intent.trees import DepTree, Terminal
from intent.utils.token import POSToken
from xigt import Igt, Tier, Item
from xigt.codecs import xigtxml
from xigt.model import XigtCorpus


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
            dt = DepTree(word.text, word_index=int(dep_index), pos=word.pos)
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
        self.id = id

    def __repr__(self):
        return '<Word "{}">'.format(self.text)

class Sentence(list):
    def __init__(self, seq=()):
        super().__init__(seq)


    def getid(self, k):
        found = None
        for w in self:
            if w.id == k:
                return w



def parse_pml_sent(sent):
    # Here we are at the root node...
    sentid = sent.get('id')

    pml_words = sent.findall(".//form")

    words = Sentence()
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
        pos       = None if container.find('pos') is None else container.find('pos').text
        parent    = find_ancestor(container.getparent())
        parentid  = parent.get('id')
        parentidx = int(parent.get('order'))
        gloss     = None if container.find('gloss') is None else container.find('gloss').text

        w = Word(text, order=order, id=nodeid, pos=pos, gloss=gloss)
        words.append(w)
        index_pairs.append((parentidx, order))
        indices_map[order] = idx+1

    for i, pair in enumerate(index_pairs):
        head, child = pair
        head = indices_map[head] if head != -1 else -1
        child= indices_map[child]
        index_pairs[i] = (head, child)

    words.sort(key=lambda x: x.order)
    return words, index_pairs

def load_xml(path):
    t = ET.parse(path)
    root = t.getroot()
    ns = strip_ns(root)
    return root

def load_sents(pml_path):
    root = load_xml(pml_path)
    sents = root.findall(".//LM[@order='-1']")
    refs = {}
    for sent in sents:
        words, indices = parse_pml_sent(sent)
        sentid = sent.get('id')
        refs[sentid] = (words, indices)


    is_glossed = root.find('.//LM/gloss') is not None

    return refs, is_glossed

def convert_pml(f_path, e_path, aln_path, out_path):

    a_root = load_xml(aln_path)
    doc_a  = a_root.find(".//reffile[@name='document_a']").get('href')
    doc_b  = a_root.find(".//reffile[@name='document_b']").get('href')

    doc_a = os.path.join(os.path.relpath(doc_a, os.path.dirname(aln_path)))
    doc_b  = os.path.join(os.path.relpath(doc_b, os.path.dirname(aln_path)))

    # Load the sentences for each document.
    a_sents, a_glossed = load_sents(doc_a)
    b_sents, b_glossed = load_sents(doc_b)

    sent_alignments = a_root.findall(".//body/LM")

    assert (a_glossed and not b_glossed) or (b_glossed and not a_glossed), "Only one file should have glosses"

    xc = XigtCorpus()

    for sent_alignment in sent_alignments:
        a_snt_ref = sent_alignment.find('./tree_a.rf').text.split('#')[1]
        b_snt_ref = sent_alignment.find('./tree_b.rf').text.split('#')[1]

        word_alignments = sent_alignment.findall('./node_alignments/LM')

        a_snt, a_edges = a_sents[a_snt_ref]
        b_snt, b_edges = b_sents[b_snt_ref]

        # -------------------------------------------
        # Start constructing the IGT Instance.
        # -------------------------------------------

        trans_snt, trans_indices = a_snt, a_edges
        gloss_snt, gloss_indices = b_snt, b_edges
        if a_glossed:
            trans_snt, trans_indices = b_snt, b_edges
            gloss_snt, gloss_indices = a_snt, a_edges

        inst = Igt(id=re.sub('s-', 'igt', a_snt_ref))
        nt   = Tier(type=ODIN_TYPE, id=NORM_ID, attributes={STATE_ATTRIBUTE:NORM_STATE})
        ll   = Item(id='n1', attributes={ODIN_TAG_ATTRIBUTE:ODIN_LANG_TAG}, text=' '.join([w.text for w in gloss_snt]))
        gl   = Item(id='n2', attributes={ODIN_TAG_ATTRIBUTE:ODIN_GLOSS_TAG}, text=' '.join([w.gloss if w.gloss else '---' for w in gloss_snt]))
        tl   = Item(id='n3', attributes={ODIN_TAG_ATTRIBUTE:ODIN_TRANS_TAG}, text=' '.join([w.text for w in trans_snt]))
        nt.extend([ll,gl,tl])
        inst.append(nt)

        # -------------------------------------------
        # Handle the phrase tiers
        # -------------------------------------------
        generate_lang_phrase_tier(inst)
        generate_trans_phrase_tier(inst)

        # -------------------------------------------
        # Now, handle the translation words.
        # -------------------------------------------
        tt = create_word_tier(ODIN_TRANS_TAG, [w.text for w in trans_snt], trans_phrase(inst)[0])
        inst.append(tt)
        add_pos_tags(inst, tt.id, [tw.pos for tw in trans_snt], tag_method=INTENT_POS_MANUAL)


        # -------------------------------------------
        # Handle the words tiers...
        # -------------------------------------------
        wt = create_word_tier(ODIN_LANG_TAG, [w.text for w in gloss_snt], lang_phrase(inst)[0])
        gwt= create_word_tier(ODIN_GLOSS_TAG,[w.gloss if w.gloss else '---' for w in gloss_snt], gl)
        inst.extend([wt, gwt])
        # Quickly set the alignment for the gloss words.
        for w, gw in zip(wt, gwt):
            gw.alignment = w.id


        add_pos_tags(inst, wt.id, [w.pos for w in gloss_snt], tag_method=INTENT_POS_MANUAL)
        add_pos_tags(inst, gwt.id,[w.pos for w in gloss_snt], tag_method=INTENT_POS_MANUAL)

        create_dt_tier(inst, assemble_ds(gloss_snt, gloss_indices), wt, INTENT_DS_MANUAL)
        create_dt_tier(inst, assemble_ds(trans_snt, trans_indices), tt, INTENT_DS_MANUAL)


        # -------------------------------------------
        # Now, the word alignments.
        # -------------------------------------------
        a = Alignment()
        for word_alignment in word_alignments:
            a_ref = word_alignment.find('./a.rf').text.split('#')[1]
            b_ref = word_alignment.find('./b.rf').text.split('#')[1]

            a_word = a_snt.getid(a_ref)
            b_word = b_snt.getid(b_ref)

            a_idx  = a_snt.index(a_word)
            b_idx  = b_snt.index(b_word)

            # Make sure the gloss is in the
            if a_glossed:
                trans_idx = b_idx
                lang_idx  = a_idx
            else:
                trans_idx = a_idx
                lang_idx  = b_idx

            a.add((trans_idx, lang_idx))

        set_bilingual_alignment(inst, trans(inst), lang(inst), a, INTENT_ALN_MANUAL)
        set_bilingual_alignment(inst, trans(inst), gloss(inst), a, INTENT_ALN_MANUAL)

        xc.append(inst)

    with open(out_path, 'w', encoding='utf-8') as f:
        xigtxml.dump(f, xc)

if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('-f', help='Foreign language file.', required=True)
    p.add_argument('-e', help='English language file.', required=True)
    p.add_argument('-a', help='Alignment file.', required=True)
    p.add_argument('-o', help='Output XIGT file', required=True)

    args = p.parse_args()

    convert_pml(args.f, args.e, args.a, args.o)