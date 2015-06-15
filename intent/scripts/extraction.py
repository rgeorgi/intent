import logging
from multiprocessing.pool import Pool
from multiprocessing import cpu_count
import sys

from intent.igt.consts import POS_TIER_TYPE, GLOSS_WORD_ID
from intent.igt.grams import write_gram
from intent.igt.igtutils import rgp
from intent.interfaces.mallet_maxent import train_txt
from intent.interfaces.stanford_tagger import train_postagger
from intent.utils.listutils import chunkIt
from intent.utils.token import GoldTagPOSToken, tokenize_string, morpheme_tokenizer
from xigt.consts import ALIGNMENT

EXTRACT_LOG = logging.getLogger("EXTRACT")

from intent.igt.rgxigt import RGCorpus, RGIgt, ProjectionException
from intent.utils.dicts import TwoLevelCountDict

__author__ = 'rgeorgi'

# =============================================================================
# EXTRACTION FUNCTION
#
# The main extraction call. This should be able to handle the classifier, cfgs,
# tagger, etc.
# =============================================================================

def extract_from_xigt(input_filelist = list, classifier_prefix=None, cfg_prefix=None, tagger_prefix=None):
    """

    Extract certain bits of supervision from a set of

    :param classifier_prefix:
    :param cfg_prefix:
    """

    # ------- Dictionaries for keeping track of gloss_pos preprocessing. --------

    word_tag_dict = TwoLevelCountDict()
    gram_tag_dict = TwoLevelCountDict()

    # =============================================================================
    # 1) SET UP
    # =============================================================================

    # Set up the classifier....
    if classifier_prefix is not None:
        print("Gathering statistics on POS tags...")

    # Set up the tagger training file...
    if tagger_prefix is not None:
        tagger_train_path = tagger_prefix+'_train.txt'
        tagger_model_path = tagger_prefix+'.tagger'

        print('Opening tagger training file at "{}"'.format(tagger_train_path))
        tagger_train_f = open(tagger_train_path, 'w', encoding='utf-8')

    cpus = cpu_count()
    p = Pool(cpus)


    # =============================================================================
    # 2) Callback
    #
    #    Callback function for processing the files after being processed by
    #    process_file
    # =============================================================================
    def callback(result):
        new_wt, new_gt, tag_sequences = result
        word_tag_dict.combine(new_wt)
        gram_tag_dict.combine(new_gt)

        # If the tagger stuff is enabled...
        if tagger_prefix is not None:
            for tag_sequence in tag_sequences:
                for token in tag_sequence:
                    content = token.seq

                    # TODO: Replacing the grammatical markers...?
                    content = content.replace('*', '')
                    content = content.replace('#', '')

                    label   = token.label

                    # FIXME: Also, should not indiscriminately drop words, but come up with a better way to fix this
                    if content.strip():
                        tagger_train_f.write('{}/{} '.format(content,label))

                tagger_train_f.write('\n')
                tagger_train_f.flush()

            for t in ['?','“','"',"''","'",',','…','/','--','-','``','`',':',';','«','»']:
                tagger_train_f.write('{}{}{}\n'.format(t,'/','PUNC'))


    for path in input_filelist:
        # p.apply_async(process_file, args=[path, classifier_prefix, cfg_prefix, tagger_prefix], callback=lambda x: merge_dicts(x, word_tag_dict, gram_tag_dict))
        callback(process_file(path, classifier_prefix, cfg_prefix, tagger_prefix))

    p.close()
    p.join()

    # =============================================================================
    # Classifier output...
    # =============================================================================

    if classifier_prefix is not None:

        # The path for the svm-light-based features.
        feat_path  =  classifier_prefix+'.feats.txt'
        class_path  = classifier_prefix+'.classifier'

        write_out_gram_dict(word_tag_dict, feat_path)

        print("Training classifier... ", end='')
        train_txt(feat_path, class_path)
        print("Complete.")

    # =============================================================================
    # Tagger output...
    # =============================================================================
    if tagger_prefix is not None:
        tagger_train_f.close()


        print('Training postagger using "{}"'.format(tagger_train_path))
        # Now, train the POStagger...
        train_postagger(tagger_train_path, tagger_model_path)
        print("Tagger training complete.")



def extract_from_instances(inst_list, classifier_prefix, feat_out_path, cfg_prefix, threshold=1):
    """
    Given a list of instances, extract the specified items.

    :param inst_list:
    :param classifier_prefix:
    :param feat_out_path:
    :param cfg_prefix:
    :param threshold:
    """
    cpus = cpu_count()
    p = Pool(cpus)

    wtd = TwoLevelCountDict()
    gtd = TwoLevelCountDict()

    for chunk in chunkIt(inst_list, cpus):
        p.apply_async(process_instances, args=[chunk, classifier_prefix, cfg_prefix], callback=lambda x: callback(x, wtd, gtd))

    p.close()
    p.join()


    # Write out the features...
    write_out_gram_dict(wtd, feat_out_path, threshold=threshold)

    # Write out the classifier...
    return train_txt(feat_out_path, classifier_prefix)

# =============================================================================
# PARALLELIZATION FUNCTIONS
#
# Functions to handle single files in parallel, and the callback to merge their
# results.
# =============================================================================

def process_file(path, classifier_prefix, cfg_prefix, tagger_prefix):
    """
    Given a XIGT-XML file, load it and do preprocessing.

    :param path:
    :return:
    """
    EXTRACT_LOG.info('Opening "{}"...'.format(path))
    xc = RGCorpus.load(path)

    # Now, iterate through each instance in the corpus...
    return process_instances(xc, classifier_prefix, cfg_prefix, tagger_prefix)

# =============================================================================
# Process the list of instances...
# =============================================================================

def process_instances(inst_list, classifier_prefix, cfg_prefix, tagger_prefix):
    """
    Given a list of instances, gather the necessary stats to train a classifier.

    :param inst_list: List of instances to process
    :type inst_list: list[RGIgt]
    :type classifier_prefix: str
    :type cfg_prefix: str
    :type tagger_prefix: str
    :return:
    """
    cur_word_tag_dict = TwoLevelCountDict()
    cur_gram_tag_dict = TwoLevelCountDict()

    lang_tag_sequences = []

    for inst in inst_list:

        # Get the gloss POS stats for the classifier...
        if classifier_prefix is not None:
            gather_gloss_pos_stats(inst, cur_word_tag_dict, cur_gram_tag_dict)

        # Also gather the tag sequences from the language line.
        if tagger_prefix is not None:
            try:
                lang_tag_sequences.append(inst.get_lang_sequence())
            except ProjectionException as pe:
                EXTRACT_LOG.warn('Unable to extract tags from instance "{}"'.format(inst.id))

    return cur_word_tag_dict, cur_gram_tag_dict, lang_tag_sequences



# =============================================================================
# Preprocessing
#
# This section is for preprocessing the gloss pos tags by limiting the tags gathered
# to only those subsets that occur frequently enough.
# =============================================================================

def gather_gloss_pos_stats(inst, word_tag_dict, gram_tag_dict):
    """
    Given an instance, look for the gloss pos tags, and save the statistics
    about them, so that we can filter by the number of times each kind was
    seen later.

    :param inst: Instance to process.
    :type inst: RGIgt
    :param word_tag_dict: This dictionary will record the number of times each (word, TAG)
                          pair has been seen.
    :type word_tag_dict: TwoLevelCountDict
    :param gram_tag_dict: This dictionary will record the number of times individual grams are seen.
    :type gram_tag_dict: TwoLevelCountDict
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

            word_tag_dict.add(word.lower(), tag)

            # Now, let's split the word into its composite grams, and add those.
            morphs = tokenize_string(word, tokenizer=morpheme_tokenizer)
            for morph in morphs:
                gram_tag_dict.add(morph.seq.lower(), tag)



# =============================================================================
# Postprocessing
#
# Now, after the grams/words have been counted up, let's filter out the grams/words
# that have been seen enough to meet our threshold, and train the classifier.
# =============================================================================

def write_out_gram_dict(gram_tag_dict, feat_path, threshold = 1):
    """
    Given the gram+tag dict, write out grams for those that have been seen enough to
    meet our threshold.

    :param gram_tag_dict:
    :type gram_tag_dict: TwoLevelCountDict
    :param feat_path:
    :param class_path:
    """

    print('Writing out svm-lite style features to "{}"...'.format(feat_path))
    feat_file = open(feat_path, 'w', encoding='utf-8')

    for gram in gram_tag_dict.keys():

        # Only write out the gram if we've seen it at least as many
        # times as in threshold.
        if gram_tag_dict.total(gram) >= threshold:
            for tag in gram_tag_dict[gram].keys():

                # Write out the gram with this tag as many times as it appears...
                for i in range(gram_tag_dict[gram][tag]):

                    gt = GoldTagPOSToken(gram, goldlabel=tag)
                    write_gram(gt, feat_next_gram=False, feat_prev_gram=False, lowercase=True, output=feat_file)
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

