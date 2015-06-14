from argparse import ArgumentParser
from collections import defaultdict
import glob
import os
import pickle
from random import shuffle, seed
import sys
from tempfile import mkdtemp
import shutil

import logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

CTN_LOG = logging.getLogger('CTN_CLASS')
CTN_LOG.setLevel(logging.DEBUG)
logging.basicConfig()


from intent.igt.metadata import set_intent_method, get_intent_method
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.pos.TagMap import TagMap
from intent.utils.env import tagger_model, proj_root
from xigt.codecs import xigtxml
from xigt.consts import ALIGNMENT





from intent.eval.pos_eval import poseval
from intent.igt.consts import GLOSS_WORD_ID, POS_TIER_TYPE, LANG_WORD_ID, GLOSS_WORD_TYPE, POS_TIER_ID, \
    INTENT_TOKEN_TYPE, INTENT_POS_PROJ, LANG_WORD_TYPE, TRANS_WORD_TYPE, TRANS_WORD_ID, MANUAL_POS, INTENT_POS_CLASS
from intent.igt.rgxigt import RGCorpus, strip_pos, RGIgt, RGTokenTier, RGTier, gen_tier_id, RGToken, \
    ProjectionTransGlossException, word_align
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.scripts.classification.xigt_to_classifier import instances_to_classifier
from intent.utils.token import POSToken, GoldTagPOSToken
from intent.igt.igtutils import rgp


__author__ = 'rgeorgi'

"""
The purpose of this module is to evaluate the POS-line classifiers trained on
"""


def eval_classifier(c, inst_list, context_feats=False, posdict=None):
    """

    :param c: The classifier
    :param inst_list: A list of Igt instances to test against. Must already have POS tags.
    """

    gold_sents = []
    eval_sents = []

    to_dump = RGCorpus()

    for inst in inst_list:

        to_tag = inst.copy()
        strip_pos(to_tag)

        # Do the classification.
        to_tag.classify_gloss_pos(c, lowercase=True,
                                  feat_next_gram=context_feats,
                                  feat_prev_gram=context_feats,
                                  posdict=posdict)


        to_dump.append(to_tag)
        # Fix the tags...
        # fix_ctn_gloss_line(to_tag, tag_method=INTENT_POS_CLASS)

        # Now, retrieve eval/gold.
        eval_tags = [v.value() for v in to_tag.get_pos_tags(GLOSS_WORD_ID, tag_method=INTENT_POS_CLASS)]
        gold_tags = [v.value() for v in inst.get_pos_tags(GLOSS_WORD_ID, tag_method=MANUAL_POS)]


        tag_tokens = [POSToken('a', label=l) for l in eval_tags]
        gold_tokens= [POSToken('a', label=l) for l in gold_tags]

        if not len(tag_tokens) == len(gold_tokens):
            print("LENGTH OF SEQUENCE IS MISMATCHED")
            continue

        gold_sents.append(gold_tokens)
        eval_sents.append(tag_tokens)


    xigtxml.dump(open('./enriched_ctn_dev.xml', 'w'), to_dump)
    return poseval(eval_sents, gold_sents, details=True,csv=True, matrix=True)



def eval_proj(xc):
    prj_sents = []
    sup_sents = []

    for inst in xc:
        fix_ctn_gloss_line(inst, tag_method=INTENT_POS_PROJ)
        # Do the projection comparison
        sup = inst.get_pos_tags(GLOSS_WORD_ID, tag_method=MANUAL_POS)
        prj = inst.get_pos_tags(GLOSS_WORD_ID, tag_method=INTENT_POS_PROJ)

        sup_tags = []
        prj_tags = []

        for s in sup:
            sup_tags.append(POSToken(s.value(), label=s.value()))
            # If the same tag occurs in the projections...
            if not prj:
                prj_tags.append(POSToken('UNALIGNED', label='UNALIGNED'))
                continue

            proj_tag = prj.find(alignment=s.attributes[ALIGNMENT])
            if proj_tag:
                prj_tags.append(POSToken(proj_tag.value(), label=proj_tag.value()))
            else:
                prj_tags.append(POSToken('UNALIGNED', label='UNALIGNED'))

        sup_sents.append(sup_tags)
        prj_sents.append(prj_tags)

    poseval(prj_sents, sup_sents, details=True)



def fix_ctn_gloss_line(inst, tag_method=None):
    """
    Given a CTN gloss line, do some specific fixes to attempt to fix the CTN tag mapping.

    :param inst:
    :type inst:RGIgt
    """

    gpos_tier = inst.get_pos_tags(GLOSS_WORD_ID, tag_method=tag_method)

    # Get the gloss words
    for gw in inst.gloss:
        new_tag = None
        if gw.value().lower() in ['foc','top','seq','add','emph','cit','rep']:
            new_tag = 'PRT'
        elif gw.value().lower() in ['but','and','or']:
            new_tag = 'CONJ'
        elif 'dem' in gw.value().lower():
            new_tag = 'PRON'
        elif gw.value().lower() in ['for','in']:
            new_tag = 'ADP'
        elif gw.value().lower() in ['the']:
            new_tag = 'DET'

        if new_tag:
            gpos = gpos_tier.find(alignment=gw.id)
            if not gpos:
                gpt = RGToken(id=gpos_tier.askItemId(), alignment=gw.id, text=new_tag)
                gpos_tier.add(gpt)
            else:
                gpos.text = new_tag



if __name__ == '__main__':

    ctn_train =  './data/xml-files/ctn/ctn_train.xml'
    ctn_dev   =  './data/xml-files/ctn/ctn_dev.xml'

    ctn_dev_processed = './data/xml-files/ctn/ctn_dev_processed.xml'
    ctn_train_processed = './data/xml-files/ctn/ctn_train_processed.xml'

    posdict   =  pickle.load(open('./data/dictionaries/CTN.dict', 'rb'))

    # print("Loading CTN Dev Corpus...", end=" ", flush=True)
    # dev_xc    = RGCorpus.load(ctn_dev)
    # print("Done.")
    #
    # print("Loading CTN Train corpus...", end=" ", flush=True)
    # train_xc    = RGCorpus.load(ctn_train)
    # print("Done.")



    print("Initializing tagger...", end=" ", flush=True)
    tagger = StanfordPOSTagger(tagger_model)
    print("Done.")

    # =============================================================================
    # 1) Start by projecting the language line to the gloss line in the dev set,
    #    remapping it from the CTN tagset to the universal tagset along the way.
    # =============================================================================
    #
    # print("Processing DEV corpus...", end=' ', flush=True)
    # for inst in dev_xc:
    #     word_align(inst.gloss, inst.lang)
    #     inst.project_lang_to_gloss(tagmap = './data/tagset_mappings/ctn.txt')
    #     fix_ctn_gloss_line(inst, tag_method=MANUAL_POS)
    #     inst.tag_trans_pos(tagger)
    #     inst.heur_align()                # Align trans/gloss lines heuristically
    #     inst.project_trans_to_gloss()    # Now, project heuristically.
    # print('done.')
    #
    # xigtxml.dump(open(ctn_dev_processed, 'w', encoding='utf-8'), dev_xc)
    #
    #
    # print("Processing TRAIN Corpus...", end=' ', flush=True)
    # # Get the language line words projected onto the gloss...
    # for inst in train_xc:
    #     word_align(inst.gloss, inst.lang)
    #     inst.project_lang_to_gloss(tagmap = './data/tagset_mappings/ctn.txt')
    #     inst.tag_trans_pos(tagger)
    #     inst.heur_align()
    #     inst.project_trans_to_gloss()
    #     fix_ctn_gloss_line(inst, tag_method=INTENT_POS_PROJ)
    #
    # print("Done.")
    #
    # xigtxml.dump(open(ctn_train_processed, 'w', encoding='utf-8'), train_xc)
    # sys.exit()

    print("Loading Processed CTN Train corpus...", end=" ", flush=True)
    train_xc    = RGCorpus.load(ctn_train_processed)
    print("Done.")

    print("Loading Processed CTN Dev corpus...", end=" ", flush=True)
    dev_xc    = RGCorpus.load(ctn_dev_processed)
    print("Done.")

    #
    # # =============================================================================
    # # 2) Train a classifier based on the projected gloss line.
    # # =============================================================================
    #

    index_list = [35,70,106,141,284,569,854,1139,1424,1708,1993,7120]

    for train_stop_index in index_list:

        train_instances = list(train_xc)[0:train_stop_index]

        print('* '*50)
        tokens = 0
        for inst in train_instances:
            tokens += len(inst.gloss)

        print("Now training with {} tokens, {} instances.".format(tokens, train_stop_index))


        print("Training Classifier...", end=" ", flush=True)
        c = instances_to_classifier(train_instances, './ctn-train.class',
                                    tag_method=MANUAL_POS,
                                    posdict=posdict,
                                    context_feats=True,
                                    feat_path='./ctn-train_feats.txt')
        print("Done.")

        # c = MalletMaxent('/Users/rgeorgi/Documents/code/dissertation/gc.classifier')
        # c = MalletMaxent('./ctn_class.class.classifier')

        print("Evaluating classifier...", end=" ", flush=True)
        eval_classifier(c, dev_xc, posdict=posdict, context_feats=True)
        print("Done.")
        # eval_proj(dev_xc)

