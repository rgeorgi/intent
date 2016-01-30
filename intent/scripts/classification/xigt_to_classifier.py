import logging
import os
import pickle
from argparse import ArgumentParser
from io import StringIO
from multiprocessing import Pool, cpu_count
from tempfile import NamedTemporaryFile

from intent.igt.grams import write_gram
from intent.igt.parsing import xc_load
from intent.interfaces.mallet_maxent import train_txt
from intent.utils.env import proj_root
from intent.utils.listutils import chunkIt
from intent.utils.token import morpheme_tokenizer, tokenize_item, GoldTagPOSToken

LOG = logging.getLogger('EXTRACT_CLASSIFIER')
logging.basicConfig()
LOG.setLevel(logging.DEBUG)

from intent.consts import POS_TIER_TYPE, GLOSS_WORD_ID
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
    xc = xc_load(f)
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

def chunk_to_features(chunk, tag_method=None, posdict=None, context_feats=False):
    """
    Method to extract the gloss-line classifier features from a subset of instances. (Useful for parallelizing)

    :param inst:
    :type inst: RGIgt
    :param tag_method:
    :param posdict:
    :param feat_path:
    :param context_feats:
    """
    out_string = StringIO()

    num_instances = 0
    # Look for the GLOSS_POS tier
    for inst in chunk:
        gpos_tier = inst.get_pos_tags(GLOSS_WORD_ID, tag_method=tag_method)
        if gpos_tier:
            num_instances += 1

            # For each token in the tier...
            for i, gp in enumerate(gpos_tier):

                if ALIGNMENT not in gp.attributes:
                    continue

                word = gp.igt.find(id=gp.attributes[ALIGNMENT]).value()
                tag  = gp.value()

                prev_word = None
                next_word = None

                if context_feats:
                    if i > 0:
                        prev_word = gp.igt.find(id=gpos_tier[i-1].attributes[ALIGNMENT]).value()

                    if i < len(gpos_tier)-1:
                        next_word = gp.igt.find(id=gpos_tier[i+1].attributes[ALIGNMENT]).value()


                # Write out features...
                t = GoldTagPOSToken(word, goldlabel=tag)
                write_gram(t,
                           feat_prev_gram=context_feats,
                           feat_next_gram=context_feats,
                           prev_gram=prev_word,
                           next_gram=next_word,
                           lowercase=True,
                           output=out_string,
                           posdict=posdict)

    return out_string.getvalue(), num_instances


def instances_to_classifier(instances, class_out_path, tag_method=None, posdict=None, feat_path=None, context_feats=False):
    """
    Given a list of IGT instances, create a gloss-line classifier from them.

    :param instances:
    :type instances: list[RGIgt]
    :param class_out_path:
    :type class_out_path: str
    :param tag_method:
    :param posdict:
    :param feat_path: Path to specify where to write out the svmlight-format feature file. If it is none, use a temp file.
    """

    # Create a temporary file for the features file that we will
    # create...
    if feat_path is None:
        ntf = NamedTemporaryFile('w', delete=True, encoding='utf-8')
    else:
        ntf = open(feat_path, 'w', encoding='utf-8')

    counts = CountDict()


    def callback(result):
        out_string, cur_instances = result
        ntf.write(out_string)
        counts.add('instances', 1)

    p = Pool(cpu_count())

    # Iterate through the instances provided
    for chunk in chunkIt(list(instances), cpu_count()):
        # p.apply_async(chunk_to_features, args=[chunk, tag_method, posdict, context_feats], callback=callback)
        callback(chunk_to_features(chunk, tag_method=tag_method, posdict=posdict, context_feats=context_feats))


    p.close()
    p.join()

    if counts['instances'] == 0:
        raise ClassifierException("No gloss POS tags found!")

    ntf.close()
    return train_txt(ntf.name, class_out_path)


if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('-o', dest='class_out', required=True, help='Output destination for the classifier.')
    p.add_argument('FILE', nargs='+', help='XIGT files to use as training.', type=globfiles)

    args = p.parse_args()
    # Flatten the argument list...
    fl = [x for f in args.FILE for x in f]

    # create_dicts(fl, args.class_out)
    process_dicts(args.class_out)