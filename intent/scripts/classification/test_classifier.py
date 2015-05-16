from argparse import ArgumentParser
from collections import defaultdict
import glob
import os
from random import shuffle, seed, Random
import sys
from tempfile import mkdtemp
import shutil

from intent.eval.pos_eval import poseval
from intent.igt.consts import GLOSS_WORD_ID, POS_TIER_TYPE
from intent.igt.rgxigt import RGCorpus, strip_pos, RGIgt
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.scripts.classification.xigt_to_classifier import instances_to_classifier
from intent.utils.env import proj_root
from intent.utils.token import POSToken


__author__ = 'rgeorgi'

"""
The purpose of this module is to evaluate the POS-line classifiers trained on
"""


def test_classifier(c, inst_list):
    """

    :param c: The classifier
    :param inst_list: A list of Igt instances to test against. Must already have POS tags.
    """

    gold_sents = []
    eval_sents = []

    for inst in inst_list:
        assert isinstance(inst, RGIgt)
        to_tag = inst.copy()
        strip_pos(to_tag)

        tags_to_eval = to_tag.classify_gloss_pos(c, lowercase=False, feat_next_gram=False, feat_prev_gram=False)
        gold_tags = [v.value() for v in inst.get_pos_tags(GLOSS_WORD_ID)]

        tag_tokens = [POSToken('a', label=l) for l in tags_to_eval]
        gold_tokens= [POSToken('a', label=l) for l in gold_tags]

        if not len(tag_tokens) == len(gold_tokens):
            continue

        gold_sents.append(gold_tokens)
        eval_sents.append(tag_tokens)

    return poseval(eval_sents, gold_sents, details=True,csv=True)


def load_xaml_data():
    instances = []

    for f in glob.glob('/Users/rgeorgi/Documents/code/treebanks/annotated_xigt/*.xml'):
        xc = RGCorpus.load(f)
        # For each instance in the xaml data, look for a gloss POS tier.
        for igt in xc:
            gpos_tier = igt.find(alignment=GLOSS_WORD_ID, type=POS_TIER_TYPE)

            # If it has gloss POS tags, let's pull them to compare against.
            if gpos_tier:
                instances.append(igt)

    return instances

def nfold_xaml():

    lang_dict = defaultdict(list)

    # -- 1) Build up the instances with POS tags, separated by language.

    for f in glob.glob('/Users/rgeorgi/Documents/code/treebanks/annotated_xigt/*.xml'):
        lang = os.path.basename(f)[:3]

        xc = RGCorpus.load(f)

        for inst in xc:
            gpos_tier = inst.find(alignment=GLOSS_WORD_ID, type=POS_TIER_TYPE)
            if gpos_tier:
                lang_dict[lang].append(inst)


    # -- 2) Create three classifiers:
    #        a) One that contains only the given language
    #        b) One that contains all but the given language
    #        c) One that contains everything but a holdout from the given language.



    odin_c = MalletMaxent('/Users/rgeorgi/Documents/code/dissertation/odin_class.classifier')

    num_splits = 2

    for lang in sorted(lang_dict.keys()):

        tmp_dir = mkdtemp()

        instances = lang_dict[lang]

        # Randomize the instances...
        shuffle(instances, random=seed(34))


        # Now, take a portion to hold out.
        split_index = int(len(instances)/2)
        lang_holdout = instances[:split_index]
        lang_rest    = instances[split_index:]

        # Now, get the other languages...
        other_langs  = []
        for other_lang in lang_dict.keys():
            if other_lang != lang:
                other_langs.extend(lang_dict[other_lang])

        # Now, let's train a separate classifier for each instance.
        same_class_path  = os.path.join(tmp_dir, 'same.class')
        other_class_path = os.path.join(tmp_dir, 'other.class')
        full_class_path  = os.path.join(tmp_dir, 'full.class')

        same_c  = instances_to_classifier(lang_rest, same_class_path)
        other_c = instances_to_classifier(other_langs, other_class_path)
        full_c  = instances_to_classifier(lang_rest+other_langs, full_class_path)

        print('{} {}'.format(lang, '*'*80))

        # Aaaand the ODIN-based classifier...

        test_classifier(same_c, lang_holdout)
        test_classifier(other_c, lang_holdout)
        test_classifier(full_c, lang_holdout)

        test_classifier(odin_c, lang_holdout)

        shutil.rmtree(tmp_dir)






if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('-c', dest='classifier', help="Path to the classifier model", required=True)


    args = p.parse_args()

    #instances = load_xaml_data()

    #classifier = MalletMaxent(args.classifier)
    #test_classifier(classifier, instances)
    nfold_xaml()