from argparse import ArgumentParser

import logging
import os
import pickle
from multiprocessing import Pool, Process
import sys
from tempfile import NamedTemporaryFile
from intent.igt.grams import write_gram
from intent.igt.igtutils import rgp
from intent.interfaces.mallet_maxent import train_txt
from intent.utils.env import proj_root
from intent.utils.token import morpheme_tokenizer, tokenize_item, GoldTagPOSToken

LOG = logging.getLogger('EXTRACT_CLASSIFIER')
logging.basicConfig()
LOG.setLevel(logging.DEBUG)

from intent.igt.consts import POS_TIER_TYPE
from intent.igt.consts import GLOSS_WORD_ID
from intent.igt.rgxigt import RGCorpus, RGIgt
from intent.utils.argutils import globfiles
from intent.utils.dicts import CountDict, TwoLevelCountDict
from xigt.consts import ALIGNMENT


class ClassifierException(Exception): pass

__author__ = 'rgeorgi'

def _process_file(f):
    c = TwoLevelCountDict()
    d = TwoLevelCountDict()
    m = TwoLevelCountDict()

    print("Processing file {}".format(f))
    xc = RGCorpus.load(f)
    for inst in xc:
        LOG.info("Now on instance {}".format(inst.id))

        # Search for the gloss POS tier, if it exists.
        gpos = inst.find(alignment=GLOSS_WORD_ID, type=POS_TIER_TYPE)

        # If a gloss POS tier was found...
        if gpos:

            # Iterate through the projected tags.
            for gp in gpos:

                word = gp.igt.find(id=gp.attributes[ALIGNMENT])

                grams = tokenize_item(word, morpheme_tokenizer)

                # Add the (gram, POSTag) pair as something that was encountered.
                for gram in grams:
                    m.add(gram.content.lower(), gp.value())


                c.add(gp.value(), word.value().lower())
                d.add(word.value().lower(), gp.value())

    return (c,d,m)

def _merge_tlcd(old, new):
    for key_a in new.keys():
        for key_b in new[key_a].keys():
            old.add(key_a, key_b, new[key_a][key_b])


c_path = os.path.join(proj_root, 'c.pickle')
d_path = os.path.join(proj_root, 'd.pickle')
m_path = os.path.join(proj_root, 'm.pickle')

def create_dicts(filelist, class_out, **kwargs):
    """
    Given a list of XIGT files, extract the gloss POS tags from them,
    then create a classifier.

    :param filelist:
    """

    c = TwoLevelCountDict()
    d = TwoLevelCountDict()
    m = TwoLevelCountDict()

    def _merge_dicts(tup):
        new_c, new_d, new_m = tup
        _merge_tlcd(c, new_c)
        _merge_tlcd(d, new_d)
        _merge_tlcd(m, new_m)
        print(len(c), len(d), len(m))

    pool = Pool(4)

    for f in filelist:
        #p = Process(target=_process_file, args=(f))
        pool.apply_async(_process_file, args=[f], callback=_merge_dicts)
        #_process_file(f, c, d, m)

    # Close the pool...
    pool.close()
    pool.join()

    # Write out the dicitonaries...
    c_f = open(c_path, 'wb')
    d_f = open(d_path, 'wb')
    m_f = open(m_path, 'wb')

    pickle.dump(c, c_f)
    pickle.dump(d, d_f)
    pickle.dump(m, m_f)
    c_f.close()

def process_dicts(class_path):
    c = pickle.load(open(c_path, 'rb'))
    d = pickle.load(open(d_path, 'rb'))
    m = pickle.load(open(m_path, 'rb'))

    print(len(c), len(d), len(m))

    # Threshold:
    thresh = 30

    # Now, we want to write out every word that we've seen at least 3 times.
    out_path = os.path.join(proj_root, 'odin_feats.txt')
    out_f = open(out_path, 'w', encoding='utf-8')
    for i, w in enumerate(d.keys()):

        if d[w].total() < thresh:
            LOG.debug("Skipping {}".format(w))
        else:
            LOG.debug("Testing {}".format(w))
            for tag in d[w].keys():

                LOG.debug("Writing out tag for {}-{}".format(w, tag))
                t = GoldTagPOSToken(w, goldlabel=tag)
                write_gram(t, output=out_f, feat_next_gram=False, feat_prev_gram=False, lowercase=True)
            out_f.flush()

    out_f.close()

    train_txt(out_path, class_path)


def instances_to_classifier(instances, class_out_path, tag_method=None):
    """
    Given a list of IGT instances, create a gloss-line classifier from them.

    :param instances: List of IGT instances.
    :type instances: list[RGIgt]
    :param class_out_path: Output path for the classifier model to train.
    """

    ntf = NamedTemporaryFile('w', delete=True)

    num_instances = 0

    for inst in instances:
        gpos_tier = inst.get_pos_tags(GLOSS_WORD_ID, tag_method=tag_method)
        if gpos_tier:
            num_instances += 1
            for gp in gpos_tier:

                # FIXME: Why do some gp not have alignments?
                if ALIGNMENT not in gp.attributes:
                    continue

                word = gp.igt.find(id=gp.attributes[ALIGNMENT]).value()
                tag  = gp.value()

                # Write out features...
                t = GoldTagPOSToken(word, goldlabel=tag)
                write_gram(t, feat_prev_gram=False, feat_next_gram=False, lowercase=True, output=ntf)

    if num_instances == 0:
        raise ClassifierException("No gloss POS tags found!")

    return train_txt(ntf.name, class_out_path)
    ntf.close()





if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('-o', dest='class_out', required=True, help='Output destination for the classifier.')
    p.add_argument('FILE', nargs='+', help='XIGT files to use as training.', type=globfiles)

    args = p.parse_args()
    # Flatten the argument list...
    fl = [x for f in args.FILE for x in f]

    # create_dicts(fl, args.class_out)
    process_dicts(args.class_out)