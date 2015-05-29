import logging
from tempfile import NamedTemporaryFile
from intent.igt.consts import POS_TIER_TYPE, GLOSS_WORD_ID
from intent.igt.grams import write_gram
from intent.interfaces.mallet_maxent import train_txt
from intent.utils.token import GoldTagPOSToken
from xigt.consts import ALIGNMENT

EXTRACT_LOG = logging.getLogger("EXTRACT")

from intent.igt.rgxigt import RGCorpus
from intent.utils.dicts import TwoLevelCountDict

__author__ = 'rgeorgi'



def extract_from_xigt(input_filelist = list, classifier_prefix=None, cfg_path=None):
    """

    Extract certain bits of supervision from a set of

    :param classifier_prefix:
    :param cfg_path:
    """

    word_tag_dict = TwoLevelCountDict()

    # Let's save the temporary file that we use to create the
    # classifier features...
    if classifier_prefix is not None:

        # The path for the svm-light-based features.
        feat_path  =  classifier_prefix+'.feats.txt'
        class_path  = classifier_prefix+'.classifier'

        feat_file = open(feat_path, 'w', encoding='utf-8')
        print('Writing svm-light style features out to "{}"'.format(feat_path))

    # Start by loading each of the files in the input files...
    for path in input_filelist:
        EXTRACT_LOG.info('Opening "{}"...'.format(path))
        xc = RGCorpus.load(path)

        # Now, iterate through each instance in the corpus...
        for inst in xc:

            # Only work with the gloss POS tags if we ask for them...
            if classifier_prefix is not None:
                process_gloss_pos_line(inst, word_tag_dict, feat_file)

    # Finally, try training the classifier on this file...
    if classifier_prefix is not None:
        print("Training classifier... ", end='')
        train_txt(feat_path, class_path)
        print("Complete.")
        feat_file.close()


def process_gloss_pos_line(inst, word_tag_dict, outfile):
    """
    Process the gloss pos line.

    :param inst:
    :param word_tag_dict:
    """
    # Grab the gloss POS tier...
    gpos_tier = inst.find(alignment=GLOSS_WORD_ID, type=POS_TIER_TYPE)

    # If this tier exists, then let's process it.
    if gpos_tier is not None:

        # Iterate over each gloss POS tag...
        for gpos in gpos_tier:

            # Skip this tag if for some reason it doesn't align with
            # a gloss word.
            if ALIGNMENT not in gpos.attributes or not gpos.alignment:
                EXTRACT_LOG.debug("No alignment found for {} in tier {} igt {}".format(gpos.id, gpos.tier.id, gpos.igt.id))
                continue

            word = gpos.igt.find(id=gpos.alignment).value()
            tag  = gpos.value()

            # Write out the features...
            t = GoldTagPOSToken(word, goldlabel=tag)
            write_gram(t, feat_prev_gram=False, feat_next_gram=False, lowercase=True, output=outfile)

