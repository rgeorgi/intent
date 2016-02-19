#!/usr/bin/env python3
import common
import os
import re
from argparse import ArgumentParser

import sys
from lxml import etree as ET

from intent.alignment.Alignment import Alignment
from intent.consts import ODIN_TYPE, STATE_ATTRIBUTE, NORM_STATE, NORM_ID, ODIN_TAG_ATTRIBUTE, ODIN_LANG_TAG, \
    ODIN_GLOSS_TAG, ODIN_TRANS_TAG, INTENT_DS_MANUAL, INTENT_POS_MANUAL, INTENT_ALN_MANUAL
from intent.igt.create_tiers import lang, gloss, generate_lang_phrase_tier, \
    generate_trans_phrase_tier, lang_phrase, create_word_tier, trans_phrase, trans
from intent.igt.igt_functions import create_dt_tier, add_pos_tags, set_bilingual_alignment
from intent.igt.igtutils import rgp
from intent.trees import DepTree
from intent.utils.fileutils import matching_files
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

def _assemble_ds(sent, index_pairs, cur_head = -1, parent_node = None, seen_indices=set(())):
    """
    :type sent: Sentence
    """
    # Get all the words that depend on the current index,
    # starting with the root (-1)

    dep_orders = [i[1] for i in index_pairs if i[0] == cur_head]
    if not dep_orders:
        return None
    elif cur_head in seen_indices:
        return None
    else:
        if parent_node is None:
            parent_node = DepTree.root()

        for dep_order in dep_orders:
            word = sent.getorder(dep_order)
            dt = DepTree(word.text, word_index=int(dep_order), pos=word.pos)
            parent_node.append(dt)
            _assemble_ds(sent, index_pairs, cur_head = dep_order, parent_node=dt, seen_indices=seen_indices|set([cur_head]))
            dt.sort(key=lambda x: x.word_index)

        return parent_node

def assemble_ds(sent, index_pairs, reorder=True):
    ds = _assemble_ds(sent, index_pairs)
    if reorder:
        for i, st in enumerate(sorted(ds.subtrees(), key=lambda x: x.word_index)):
            st._word_index = i+1
    return ds


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

    def getorder(self, k):
        found = None
        for w in self:
            if  w.order == k:
                return w

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
    # -------------------------------------------
    for word in pml_words:
        container = word.getparent()
        nodeid    = container.get('id')
        order     = int(container.get('order'))
        text      = word.text
        pos       = None if container.find('pos') is None else container.find('pos').text
        parent    = find_ancestor(container.getparent())
        parentid  = parent.get('id')
        parent_order = int(parent.get('order'))
        gloss     = None if container.find('gloss') is None else container.find('gloss').text

        w = Word(text, order=order, id=nodeid, pos=pos, gloss=gloss)
        words.append(w)
        index_pairs.append((parent_order, order))

    words.sort(key=lambda x: x.order)
    return words, index_pairs

def load_xml(path):
    t = ET.parse(path)
    root = t.getroot()
    ns = strip_ns(root)
    return root

def load_sents(pml_path):
    """

    :rtype: tuple[dict[str,Sentence],bool]
    """
    root = load_xml(pml_path)
    root_idx = -1
    sents = root.findall(".//LM[@order='-1']")
    refs = {}
    for sent in sents:
        words, indices = parse_pml_sent(sent)
        sentid = sent.get('id')
        refs[sentid] = (words, indices)


    is_glossed = root.find('.//LM/gloss') is not None

    return refs, is_glossed

def retrieve_hindi():
    hindi_file = '/Users/rgeorgi/Documents/treebanks/hindi_ds/Glosses-DSguidelines.txt'
    igt_data = {}
    with open(hindi_file, 'r', encoding='utf-8', errors='replace') as f:
        data = f.read()
        instances = re.findall('<Sentence[\s\S]+?</Sentence>', data)
        for instance in instances:
            inst_id = re.search('sentence id="(.*?)">', instance, flags=re.I).group(1)
            lang    = re.search('<original>(.*?)</original>', instance, flags=re.I).group(1)
            gloss   = re.search('<gloss>(.*?)</gloss>', instance, flags=re.I).group(1)
            trans   = re.search('<translation>(.*?)</tr', instance, flags=re.I).group(1)
            igt_data[inst_id] = [None, lang, gloss, trans]
    return igt_data

def retrieve_naacl():
    naacl_dir = '/Users/rgeorgi/Documents/treebanks/NAACL_igt'
    igt_data = {}
    for oracle_path in matching_files(naacl_dir, '^or\.111$', recursive=True):
        print(oracle_path)
        with open(oracle_path, 'r', encoding='utf-8', errors='replace') as f:
            data = f.read()
            instances = re.findall('(Igt_id=[\s\S]+?)\s+########', data)
            for instance in instances:
                inst_id = re.search('Igt_id=([0-9]+)', instance).group(1)
                igt_data[inst_id] = instance.split('\n')

    return igt_data

def convert_pml(aln_path, out_path, hindi=True):

    if hindi:
        igt_data = retrieve_hindi()
    else:
        igt_data = retrieve_naacl()

    a_root = load_xml(aln_path)
    doc_a  = a_root.find(".//reffile[@name='document_a']").get('href')
    doc_b  = a_root.find(".//reffile[@name='document_b']").get('href')



    doc_a = os.path.join(os.path.join(os.path.dirname(aln_path), doc_a))
    doc_b  = os.path.join(os.path.join(os.path.dirname(aln_path), doc_b))

    # Load the sentences for each document.
    a_sents, a_glossed = load_sents(doc_a)
    b_sents, b_glossed = load_sents(doc_b)



    sent_alignments = a_root.findall(".//body/LM")

    assert (a_glossed and not b_glossed) or (b_glossed and not a_glossed), "Only one file should have glosses"

    xc = XigtCorpus()

    for sent_alignment in sent_alignments:

        # Get the sentence id...
        aln_id = sent_alignment.attrib.get('id')
        a_snt_id = re.search('^.+?-(.*)$', aln_id).group(1)
        if a_snt_id not in igt_data:
            continue

        # Get the text and tokens from the naacl data.
        pre_txt, lang_txt, gloss_txt, trans_txt = igt_data[a_snt_id]
        lang_tokens = lang_txt.split()
        gloss_tokens = gloss_txt.split()
        trans_tokens = trans_txt.split()

        a_snt_ref = sent_alignment.find('./tree_a.rf').text.split('#')[1]
        b_snt_ref = sent_alignment.find('./tree_b.rf').text.split('#')[1]

        word_alignments = sent_alignment.findall('./node_alignments/LM')

        a_snt, a_edges = a_sents[a_snt_ref]
        b_snt, b_edges = b_sents[b_snt_ref]

        assert isinstance(a_snt, Sentence)
        assert isinstance(b_snt, Sentence)
        # -------------------------------------------
        # Skip sentences if they are not found for whatever reason
        # -------------------------------------------
        if not a_snt or not b_snt:
            continue

        # -------------------------------------------
        # Start constructing the IGT Instance.
        # -------------------------------------------

        trans_snt, trans_indices = a_snt, a_edges
        gloss_snt, gloss_indices = b_snt, b_edges
        if a_glossed:
            trans_snt, trans_indices = b_snt, b_edges
            gloss_snt, gloss_indices = a_snt, a_edges

        # Hindi stuff...
        if hindi:
            lang_tokens = [w.text for w in gloss_snt]
            lang_postags   = [w.pos  for w in gloss_snt]
            lang_txt    = ' '.join(lang_tokens)

            trans_tokens = [w.text for w in trans_snt]
            trans_postags   = [w.pos  for w in trans_snt]
            trans_txt    = ' '.join(trans_tokens)

            gloss_tokens  = [w.gloss if w.gloss else 'NULL' for w in gloss_snt]
            gloss_postags = lang_postags
            gloss_txt     = ' '.join(gloss_tokens)



        inst = Igt(id=re.sub('s-', 'igt', a_snt_ref))
        nt   = Tier(type=ODIN_TYPE, id=NORM_ID, attributes={STATE_ATTRIBUTE:NORM_STATE})
        ll   = Item(id='n1', attributes={ODIN_TAG_ATTRIBUTE:ODIN_LANG_TAG}, text=lang_txt)
        gl   = Item(id='n2', attributes={ODIN_TAG_ATTRIBUTE:ODIN_GLOSS_TAG}, text=gloss_txt)
        tl   = Item(id='n3', attributes={ODIN_TAG_ATTRIBUTE:ODIN_TRANS_TAG}, text=trans_txt)
        nt.extend([ll,gl,tl])
        inst.append(nt)


        # -------------------------------------------
        # Handle the phrase tiers
        # -------------------------------------------
        generate_lang_phrase_tier(inst)
        generate_trans_phrase_tier(inst)

        def process_postags(sent, tokens):
            postags = []
            for i, token in enumerate(tokens):
                word = sent.getorder(i+1)
                if word is None:
                    postags.append(None)
                else:
                    postags.append(word.pos)
            return postags

        # -------------------------------------------
        # Now, handle the translation words.
        # -------------------------------------------
        tt = create_word_tier(ODIN_TRANS_TAG, trans_tokens, trans_phrase(inst)[0])
        inst.append(tt)

        if not hindi:
            trans_postags = process_postags(trans_snt, trans_tokens)

        add_pos_tags(inst, tt.id, trans_postags, tag_method=INTENT_POS_MANUAL)


        # -------------------------------------------
        # Handle the words tiers...
        # -------------------------------------------
        wt = create_word_tier(ODIN_LANG_TAG, lang_tokens, lang_phrase(inst)[0])
        gwt= create_word_tier(ODIN_GLOSS_TAG, gloss_tokens, gl)
        inst.extend([wt, gwt])
        # Quickly set the alignment for the gloss words.
        for w, gw in zip(wt, gwt):
            gw.alignment = w.id


        if not hindi:
            lang_postags = process_postags(gloss_snt, gloss_tokens)
            gloss_postags = lang_postags

        add_pos_tags(inst, wt.id, lang_postags, tag_method=INTENT_POS_MANUAL)
        add_pos_tags(inst, gwt.id, gloss_postags, tag_method=INTENT_POS_MANUAL)

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

            if a_word is None or b_word is None:
                continue

            if not hindi:
                a_idx  = a_word.order
                b_idx  = b_word.order
            else:
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
    p.add_argument('-a', help='Alignment file.', required=True)
    p.add_argument('-o', help='Output XIGT file', required=True)

    args = p.parse_args()

    convert_pml(args.a, args.o)
