from argparse import ArgumentParser
from collections import defaultdict
import glob
import os
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
    INTENT_TOKEN_TYPE, INTENT_POS_PROJ, LANG_WORD_TYPE, TRANS_WORD_TYPE, TRANS_WORD_ID, MANUAL_POS
from intent.igt.rgxigt import RGCorpus, strip_pos, RGIgt, RGTokenTier, RGTier, gen_tier_id, RGToken, \
    ProjectionTransGlossException
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.scripts.classification.xigt_to_classifier import instances_to_classifier
from intent.utils.token import POSToken, GoldTagPOSToken
from intent.igt.igtutils import rgp


__author__ = 'rgeorgi'

"""
The purpose of this module is to evaluate the POS-line classifiers trained on
"""


def eval_classifier(c, inst_list):
    """

    :param c: The classifier
    :param inst_list: A list of Igt instances to test against. Must already have POS tags.
    """

    gold_sents = []
    eval_sents = []

    for inst in inst_list:

        to_tag = inst.copy()
        strip_pos(to_tag)

        tags_to_eval = to_tag.classify_gloss_pos(c, lowercase=True, feat_next_gram=False, feat_prev_gram=False)
        gold_tags = [v.value() for v in inst.get_pos_tags(GLOSS_WORD_ID, tag_method=MANUAL_POS)]


        tag_tokens = [POSToken('a', label=l) for l in tags_to_eval]
        gold_tokens= [POSToken('a', label=l) for l in gold_tags]

        if not len(tag_tokens) == len(gold_tokens):
            print("LENGTH OF SEQUENCE IS MISMATCHED")
            continue

        gold_sents.append(gold_tokens)
        eval_sents.append(tag_tokens)

    return poseval(eval_sents, gold_sents, details=True,csv=True)


def load_xaml_data():
    instances = []

    for f in glob.glob('/Users/rgeorgi/Documents/code/treebanks/annotated_xigt/*.xml'):
        xc = RGCorpus.load(f, basic_processing=True)
        # For each instance in the xaml data, look for a gloss POS tier.
        for igt in xc:
            gpos_tier = igt.find(alignment=GLOSS_WORD_ID, type=POS_TIER_TYPE)

            # If it has gloss POS tags, let's pull them to compare against.
            if gpos_tier:
                instances.append(igt)

    return instances

def eval_pos_tiers(eval_tier, gold_tier):
    """
    Given two POS tag tiers, return eval.

    :param eval_tier:
    :param pos_tier:
    """
    idmap = {}

    # Get
    for eval_pos in eval_tier:
        idmap[eval_pos.attributes[ALIGNMENT]] = eval_pos.value()

    matches = 0
    compares= 0
    unaligned = 0

    for gold_pos in gold_tier:
        gold_id = gold_pos.attributes[ALIGNMENT]

        if gold_id not in idmap:
            unaligned += 1
        elif idmap[gold_id] == gold_pos.value():
            matches += 1

        if gold_id in idmap:
            print(gold_pos.value(), idmap[gold_id])

        compares += 1

    return (matches, compares, unaligned)

def enrich_multiple(pathlist, tagger, tagmap):
    instances = []
    for path in pathlist:
        xc = RGCorpus.load(path, basic_processing=True)
        instances += list(xc)

    return enrich_ctn(instances, tagger, tagmap)

def enrich_ctn(instances, tagger, tagmap):

    xc = RGCorpus()

    for i, inst in enumerate(instances):
        CTN_LOG.debug('Processing instance #{} - id({})'.format(i, inst.id))
        w_tier = inst.find(type=TRANS_WORD_TYPE, id=TRANS_WORD_ID)
        w_tier.delete()
        inst.trans

        assert isinstance(inst, RGIgt)
        wpos_tier = inst.get_pos_tags(LANG_WORD_ID)

        if wpos_tier:

            inst.heur_align()

            # Do projection
            inst.tag_trans_pos(tagger)
            try:
                inst.project_trans_to_gloss()
            except ProjectionTransGlossException as ptge:
                pass
            else:
                # Do the remapping....
                gw_tier  = inst.find(id=GLOSS_WORD_ID)
                proj_pos = inst.get_pos_tags(GLOSS_WORD_ID, INTENT_POS_PROJ)

                for gw in gw_tier:
                    new_tag = None
                    if gw.value().lower() in ['yes','no','not','seq','top','foc','emph','add','filler']:
                        new_tag = 'PRT'
                        CTN_LOG.debug("PRT gloss identified.")
                    elif gw.value().lower() in ['and','but','or']:
                        CTN_LOG.debug("CONJ gloss identified.")
                        new_tag = 'CONJ'

                    if new_tag is not None:

                        # If a tag already exists...
                        aligned_tag = proj_pos.find(alignment=gw.id)

                        if aligned_tag is not None:
                            aligned_tag.text = new_tag
                        else:
                            t = RGToken(id=proj_pos.askItemId(), alignment=gw.id, text=new_tag)
                            proj_pos.append(t)


            # Create the (supervised) gloss tier from the language tier...
            gp_tier = RGTokenTier(type=POS_TIER_TYPE,
                                    id=gen_tier_id(inst, POS_TIER_ID, tier_type=POS_TIER_TYPE, alignment=inst.gloss.id),
                                    alignment=inst.gloss.id)

            set_intent_method(gp_tier, MANUAL_POS)

            for wpos in wpos_tier:

                old_tag = wpos.value()
                tag = tagmap[old_tag]

                lw = inst.find(id=wpos.attributes[ALIGNMENT])

                gw = inst.find(alignment=wpos.attributes[ALIGNMENT], others=[lambda x: hasattr(x, 'tier') and x.tier.type == GLOSS_WORD_TYPE])

                # Check for remapping of gloss words to CONJ...
                if gw.value().lower() in ['but', 'and', 'or']:
                    tag = 'CONJ'

                gt = RGToken(id=gp_tier.askItemId(), alignment=gw.id, text=tag)

                gp_tier.append(gt)

                # gp_file.write('{}\t{}\t{}\t{}\n'.format(lw.value(), gw.value(), old_tag, tag))

            inst.append(gp_tier)
        xc.append(inst)

    return xc

def eval_proj(xc):
    prj_sents = []
    sup_sents = []

    for inst in xc:
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

dev_enriched_path      = '/Users/rgeorgi/Documents/code/dissertation/examples/ctn/ctn_dev_enriched.xml'
train_enriched_path    = '/Users/rgeorgi/Documents/code/dissertation/examples/ctn/ctn_train_enriched.xml'
devtrain_enriched_path = '/Users/rgeorgi/Documents/code/dissertation/examples/ctn/ctn_devtrain_enriched.xml'

def enrich_all_ctn():

    lang_dict = defaultdict(list)

    # -- 1) Initialize the tags
    tm = TagMap('/Users/rgeorgi/Documents/code/dissertation/data/tagset_mappings/ctn.txt')
    st = StanfordPOSTagger(tagger_model)

    # Some hardcoded test files...
    dev = '/Users/rgeorgi/Documents/code/dissertation/examples/ctn/ctn_dev.xml'
    train = '/Users/rgeorgi/Documents/code/dissertation/examples/ctn/ctn_train.xml'
    small = '/Users/rgeorgi/Documents/code/dissertation/examples/ctn-train_small.xml'
    full = '/Users/rgeorgi/Documents/code/dissertation/examples/ctn-train.xml'

    dev_c = enrich_multiple([dev], st, tm)
    train_c = enrich_multiple([train], st, tm)
    devtrain_c = enrich_multiple([dev, train], st, tm)
    sys.exit()

    # Now, let's dump out those enriched files...
    dev_enriched      = open(dev_enriched_path, 'w', encoding='utf-8')
    train_enriched    = open(train_enriched_path, 'w', encoding='utf-8')
    devtrain_enriched = open(devtrain_enriched_path, 'w', encoding='utf-8')

    xigtxml.dump(dev_enriched, dev_c)
    xigtxml.dump(train_enriched, train_c)
    xigtxml.dump(devtrain_enriched, devtrain_c)

def eval_ctn():

    dev_c      = RGCorpus.load(dev_enriched_path)
    train_c    = RGCorpus.load(train_enriched_path)
    devtrain_c = RGCorpus.load(devtrain_enriched_path)

    eval_proj(dev_c)
    eval_proj(train_c)
    eval_proj(devtrain_c)


    #sys.exit()

    # eval_proj(dev_c)
    # eval_proj(devtrain_c)
    # sys.exit()

    dev_classifier = instances_to_classifier(dev_c, os.path.join(proj_root, 'ctn_dev.classifier'))
    eval_classifier(dev_classifier, dev_c)

    devtrain_classifier = instances_to_classifier(devtrain_c, os.path.join(proj_root, 'ctn_devtrain.classifier'))
    eval_classifier(devtrain_classifier, dev_c)

    train_classifier = instances_to_classifier(train_c, os.path.join(proj_root, 'ctn_train.classifier'))
    eval_classifier(train_classifier, dev_c)

    #xigtxml.dump(open(os.path.join(proj_root, 'ctn_dump.xml'), 'w', encoding='utf-8'), xc)
    sys.exit()


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

        eval_classifier(same_c, lang_holdout)
        eval_classifier(other_c, lang_holdout)
        eval_classifier(full_c, lang_holdout)

        eval_classifier(odin_c, lang_holdout)

        shutil.rmtree(tmp_dir)






if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('-c', dest='classifier', help="Path to the classifier model", required=True)


    args = p.parse_args()

    #instances = load_xaml_data()

    #classifier = MalletMaxent(args.classifier)
    #test_classifier(classifier, instances)
    CTN_LOG.setLevel(logging.DEBUG)
    #enrich_all_ctn()

    eval_ctn()