import logging
import os

import re
from collections import defaultdict

from os import unlink

from intent.igt.create_tiers import gloss, gloss_tag_tier, lang_tag_tier, trans, glosses
from intent.igt.exceptions import RGXigtException, ProjectionException, NoNormLineException
from intent.igt.igtutils import clean_lang_token
from intent.igt.parsing import xc_load
from intent.igt.references import xigt_find
from intent.pos.TagMap import TagMap
from intent.trees import to_conll
from intent.utils import fileutils
from intent.utils.env import posdict, load_posdict
from xigt.codecs import xigtxml
from xigt.consts import *
from xigt.model import Igt, Item

from intent.consts import *
from intent.igt.grams import write_gram
from intent.igt.igt_functions import get_lang_ds, pos_tag_tier, lang, get_lang_ps, add_gloss_lang_alignments, \
    project_lang_to_gloss, tier_text, get_trans_glosses_alignment, heur_align_inst, get_trans_gloss_wordpairs, \
    get_trans_gloss_lang_alignment, word_align, handle_unknown_pos, get_trans_aligned_wordpairs
from intent.interfaces.mallet_maxent import train_txt
from intent.interfaces.mst_parser import MSTParser
from intent.interfaces.stanford_tagger import train_postagger
from intent.utils.token import GoldTagPOSToken, tokenize_string, morpheme_tokenizer


EXTRACT_LOG = logging.getLogger("EXTRACT")

from intent.utils.dicts import TwoLevelCountDict

__author__ = 'rgeorgi'

def extract_parser_from_instance(inst: Igt, output_stream, pos_source, tm):
    """
    Given an IGT instance, extract the projected dependency structure from
    it (along with the POS tags from the given pos_source)

    :param inst: Input instance
    :param output_stream: The output stream to write the training data to.
    """
    extracted = 0
    try:
        ds = get_lang_ds(inst, pos_source=pos_source, unk_pos_handling=None)
        if ds is not None:
            conll_string = to_conll(ds, lang(inst), lowercase=True, match_punc=True, clean_token=True, unk_pos='UNK', tagmap=tm)
            output_stream.write(conll_string+'\n\n')
            output_stream.flush()
            extracted += 1

    except RuntimeError as re:
        print(re)
        EXTRACT_LOG.error("Runtime error in instance {}".format(inst.id))
    except RGXigtException as rgxe:
        EXTRACT_LOG.warn('Instance "{}" failed with "{}"'.format(inst.id, rgxe))

    return extracted


def extract_tagger_from_instance(inst: Igt, output_stream, pos_source, tm):
    """
    Given an instance, retrieve the language-line words and POS tags.

    :param inst:
    :param output_stream:
    :param pos_source:
    """
    lang_pos_tags = lang_tag_tier(inst, tag_method=pos_source)
    lang_words     = lang(inst)

    training_sentences = 0

    # -------------------------------------------
    # Only try extracting if there are in fact valid POS tags.
    # -------------------------------------------
    if lang_pos_tags:

        first = True
        for lang_word in lang_words:

            lang_pos_tag = None
            if lang_pos_tags is not None:
                lang_pos_tag = xigt_find(lang_pos_tags, alignment=lang_word.id)

            tag_string = lang_pos_tag.value() if lang_pos_tag is not None else handle_unknown_pos(inst, lang_word)
            if tag_string and tm:
                tag_string = tm[tag_string]

            word_string = lang_word.value()

            # -------------------------------------------
            # Do some cleaning on the output words
            # -------------------------------------------
            word_string = clean_lang_token(word_string, lowercase=True)

            # For every instance after the first,
            # add a space.
            out_str = ' {}/{}'
            if first:
                first = False
                out_str = out_str.strip()

            output_stream.write(out_str.format(word_string, tag_string))
        output_stream.write('\n')
        output_stream.flush()
        training_sentences += 1

    return training_sentences



def extract_sents_from_inst(inst: Igt, out_src, out_tgt, aln_method=None, no_alignment_heur = True, sent_type=SENT_TYPE_T_G):
    """
    Extract parallel sentences from an instance. Either:

    1) Translation--Gloss
    2) Translation--Language
    """

    # -------------------------------------------
    # 1) Get the source string (translation)
    # -------------------------------------------
    src_str = tier_text(trans(inst), remove_whitespace_inside_tokens=True).lower()


    # -------------------------------------------
    # 2) Decide whether the target string is gloss or language.
    # -------------------------------------------
    if sent_type == SENT_TYPE_T_L:
        tgt_str = tier_text(lang(inst), remove_whitespace_inside_tokens=True).lower()
    elif sent_type == SENT_TYPE_T_G:
        tgt_str = tier_text(gloss(inst), remove_whitespace_inside_tokens=True).lower()
    else:
        raise Exception("Invalid sent type")

    # -------------------------------------------
    # 3) Write the choice out to disk.
    # -------------------------------------------
    out_src.write(src_str + '\n')
    out_tgt.write(tgt_str + '\n')
    out_src.flush()
    out_tgt.flush()

    # -------------------------------------------
    # 4) Add heuristic alignments, if asked for.
    # -------------------------------------------
    if not no_alignment_heur:

        pairs = get_trans_aligned_wordpairs(inst, aln_method=aln_method, add_align=True, sent_type=sent_type)
        for src_word, tgt_word in pairs:
            out_src.write(src_word.lower() + '\n')
            out_tgt.write(tgt_word.lower() + '\n')


class SubwordDict(object):
    def __init__(self):
        self.sw_dict = defaultdict(lambda: dict())

    def keys(self):
        return self.sw_dict.keys()

    def __getitem__(self, k):
        return self.sw_dict[k]

    def add_word_tag(self, word, tag, prev_word=None, next_word=None, count=1):
        for subword in tokenize_string(word, tokenizer=morpheme_tokenizer):
            subword = subword.seq
            if tag not in self.sw_dict[subword].keys():
                self.sw_dict[subword][tag] = {'contexts':[(prev_word,next_word)], 'count':count}
            else:
                self.sw_dict[subword][tag]['contexts'].append((prev_word, next_word))
                self.sw_dict[subword][tag]['count'] += count


# =============================================================================
# EXTRACTION FUNCTION
#
# The main extraction call. This should be able to handle the classifier, cfgs,
# tagger, etc.
# =============================================================================

def extract_from_xigt(input_filelist = list, classifier_prefix=None, classifier_feats=CLASS_FEATS_DEFAULT,
                      cfg_path=None, tagger_prefix=None,
                      dep_prefix=None, pos_method=None, aln_method=None,
                      sent_prefix=None, no_alignment_heur=False, sent_type=SENT_TYPE_T_G, **kwargs):

    # ------- Dictionaries for keeping track of gloss_pos preprocessing. --------

    # This dictionary will first, be a list of "words" (full word-level)
    subword_dict = SubwordDict()

    # -------------------------------------------
    # Map the argument provided for "dep_pos" to
    # the alignment type that will be searched
    # -------------------------------------------
    use_pos = ARG_POS_MAP[pos_method]
    use_aln = ALN_ARG_MAP[aln_method]

    # -------------------------------------------
    # Get the tagset mapping if provided
    # -------------------------------------------
    tagpath = kwargs.get('tagmap')
    tm = None if tagpath is None else TagMap(tagpath)

    # =============================================================================
    # 1) SET UP
    # =============================================================================

    extracted_tagged_snts = 0
    extracted_parsed_snts = 0
    inst_count = 0


    if dep_prefix or tagger_prefix:
        if use_pos == ARG_POS_NONE:
            EXTRACT_LOG.log(NORM_LEVEL, 'Not using POS tags for extraction.')
        elif use_pos is None:
            EXTRACT_LOG.log(NORM_LEVEL, "Using any available POS tags for extraction.")
        else:
            EXTRACT_LOG.log(NORM_LEVEL, 'Using language line tags produced by method "{}"...'.format(use_pos))


    # Set up the classifier....
    if classifier_prefix is not None:
        EXTRACT_LOG.log(NORM_LEVEL, "Gathering statistics on POS tags...")

    # Set up the tagger training file...
    if tagger_prefix is not None:
        tagger_train_path = tagger_prefix+'_tagger_train.txt'
        tagger_model_path = tagger_prefix+'.tagger'


        EXTRACT_LOG.log(NORM_LEVEL, 'Opening tagger training file at "{}"'.format(tagger_train_path))
        fileutils.makedirs(os.path.dirname(tagger_train_path))
        tagger_train_f = open(tagger_train_path, 'w', encoding='utf-8')

    # Set up the dependency parser output if it's specified...
    dep_train_f = None
    dep_train_path = None
    if dep_prefix is not None:
        dep_train_path = dep_prefix+'_dep_train.txt'
        EXTRACT_LOG.log(NORM_LEVEL, 'Writing dependency parser training data to "{}"'.format(dep_train_path))

        # Make the containing directory if it does not exist.
        fileutils.makedirs(os.path.dirname(dep_prefix))

        # Write out the training file.
        dep_train_f = open(dep_train_path, 'w', encoding='utf-8')

    # Set up the files for writing out alignment.
    if sent_prefix is not None:
        fileutils.makedirs(os.path.dirname(sent_prefix))
        e_f = open(sent_prefix + '_e.txt', 'w', encoding='utf-8')
        f_f = open(sent_prefix + '_f.txt', 'w', encoding='utf-8')

    # Set up the CFG path for writing.
    if cfg_path is not None:
        fileutils.makedirs(os.path.dirname(cfg_path))
        cfg_f = open(cfg_path, 'w', encoding='utf-8')

    # -------------------------------------------
    # Iterate over the provided files.
    # -------------------------------------------
    for path in input_filelist:
        xc = xc_load(path, mode=INCREMENTAL)

        # -------------------------------------------
        # Do the appropriate extraction for each
        # -------------------------------------------
        for inst in xc:
            inst_count += 1
            if tagger_prefix is not None:
                extracted_tagged_snts += extract_tagger_from_instance(inst, tagger_train_f, use_pos, tm)

            if dep_prefix is not None:
                extracted_parsed_snts += extract_parser_from_instance(inst, dep_train_f, use_pos, tm)

            if classifier_prefix is not None:
                gather_gloss_pos_stats(inst, subword_dict)

            if sent_prefix is not None:
                try:
                    extract_sents_from_inst(inst, e_f, f_f, no_alignment_heur=no_alignment_heur,
                                            sent_type=sent_type, aln_method=use_aln)
                except NoNormLineException:
                    pass

            if cfg_path:
                extract_cfg_rules_from_inst(inst, cfg_f)

    # -------------------------------------------
    # After looping
    # -------------------------------------------

    EXTRACT_LOG.log(NORM_LEVEL, "{} instances processed.".format(inst_count))

    # Add punctuation marks to the tagger.
    if tagger_prefix is not None:
        if extracted_tagged_snts == 0:
            EXTRACT_LOG.error("No tags were found. Not writing out file.")
            tagger_train_f.close()
            unlink(tagger_train_path)
        else:
            for t in ['?','“','"',"''","'",',','…','/','--','-','``','`',':',';','«','»']:
                tagger_train_f.write('{}{}{}\n'.format(t,'/','PUNC'))
            tagger_train_f.close()
            EXTRACT_LOG.log(NORM_LEVEL, 'Training postagger using "{}"'.format(tagger_train_path))
            # Now, train the POStagger...
            train_postagger(tagger_train_path, tagger_model_path)
            EXTRACT_LOG.log(NORM_LEVEL, "Tagger training complete.")



    # =============================================================================
    # Classifier output...
    # =============================================================================

    if classifier_prefix is not None:

        # The path for the svm-light-based features.
        class_dir  = os.path.dirname(classifier_prefix)
        os.makedirs(class_dir, exist_ok=True)

        feat_path  =  classifier_prefix+'.feats.txt'
        class_path  = classifier_prefix+'.classifier'

        write_out_gram_dict(subword_dict, feat_path, classifier_feats)

        EXTRACT_LOG.log(NORM_LEVEL, "Training classifier.")
        train_txt(feat_path, class_path)
        EXTRACT_LOG.log(NORM_LEVEL, "Complete.")

    if cfg_path:
        cfg_f.close()

    # -------------------------------------------
    # Train
    # -------------------------------------------
    if dep_prefix:
        if extracted_parsed_snts == 0:
            EXTRACT_LOG.error("No dependency parses were found. Not training parser.")
            dep_train_f.close()
            unlink(dep_train_path)
        else:
            EXTRACT_LOG.log(NORM_LEVEL, "{} dependency parses found. Training parser...".format(extracted_parsed_snts))
            dep_train_f.close()
            dep_parser_path = dep_prefix+'.depparser'
            mp = MSTParser()
            mp.train(dep_train_path, dep_parser_path)

def extract_cfg_rules_from_inst(inst, out_f):
    """
    Given an instance, write out the cfg rules.
    """
    t = get_lang_ps(inst)
    if t is not None:
        for prod in t.productions():
            out_f.write('{}\n'.format(prod))
        out_f.flush()

# =============================================================================
# Preprocessing
#
# This section is for preprocessing the gloss pos tags by limiting the tags gathered
# to only those subsets that occur frequently enough.
# =============================================================================

def gather_gloss_pos_stats(inst, subword_dict):
    """
    Given an instance, look for the gloss pos tags, and save the statistics
    about them, so that we can filter by the number of times each kind was
    seen later.

    :param inst: Instance to process.
    :type inst: RGIgt
    :param subword_dict: This dictionary will record the number of times each (word, TAG)
                          pair has been seen.
    :type subword_dict: SubwordDict
    :param gram_tag_dict: This dictionary will record the number of times individual grams are seen.
    :type gram_tag_dict: TwoLevelCountDict
    """

    # Grab the gloss POS tier...
    gpos_tier = gloss_tag_tier(inst)
    lpos_tier = lang_tag_tier(inst)
    gw_tier = gloss(inst)

    # If there are POS tags on the language line but not the gloss line...
    if gpos_tier is None and lpos_tier is not None:
        add_gloss_lang_alignments(inst)
        project_lang_to_gloss(inst)
        gpos_tier = gloss_tag_tier(inst)


    # If this tier exists, then let's process it.
    if gpos_tier is not None:

        # Iterate over each gloss POS tag...
        for i, gw in enumerate(gw_tier):
            tag = xigt_find(inst, alignment=gw.id)

            if tag is None:
                continue

            prev_word = gw_tier[i-1].value().lower() if i > 0 else None
            next_word = gw_tier[i+1].value().lower() if i < len(gw_tier)-1 else None

            subword_dict.add_word_tag(gw.value().lower(), tag.value(), prev_word, next_word)



# =============================================================================
# Postprocessing
#
# Now, after the grams/words have been counted up, let's filter out the grams/words
# that have been seen enough to meet our threshold, and train the classifier.
# =============================================================================

def write_out_gram_dict(subword_dict, feat_path, feat_list, threshold = 1):
    """
    Given the gram+tag dict, write out grams for those that have been seen enough to
    meet our threshold.

    :param subword_dict:
    :type subword_dict: TwoLevelCountDict
    :param feat_path:
    :param class_path:
    """

    EXTRACT_LOG.log(NORM_LEVEL, 'Writing out svm-lite style features to "{}"...'.format(feat_path))
    feat_file = open(feat_path, 'w', encoding='utf-8')

    # Load the posdict if needed...
    pd = load_posdict() if (CLASS_FEATS_DICT in feat_list) or (CLASS_FEATS_PDICT in feat_list) or (CLASS_FEATS_NDICT in feat_list) else False

    for subword in subword_dict.keys():
        for tag in subword_dict[subword].keys():
            # Write out the gram with this tag as many times as it appears...
            for prev_word, next_word in subword_dict[subword][tag]['contexts']:
                gt = GoldTagPOSToken(subword, goldlabel=tag)

                # -------------------------------------------
                # Now, vary the features depending on whats in the list
                # -------------------------------------------
                if CLASS_FEATS_NEXSW not in feat_list:
                    next_word = None
                if CLASS_FEATS_PRESW not in feat_list:
                    prev_word = None




                write_gram(gt, feat_next_gram=next_word, feat_prev_gram=prev_word, lowercase=True,
                           feat_suffix=CLASS_FEATS_SUF in feat_list,
                           feat_prefix=CLASS_FEATS_PRE in feat_list,
                           feat_has_number=CLASS_FEATS_NUM in feat_list,
                           feat_morph_num=CLASS_FEATS_NUMSW in feat_list,
                           feat_prev_gram_dict=CLASS_FEATS_PDICT in feat_list,
                           feat_next_gram_dict=CLASS_FEATS_NDICT in feat_list,
                           feat_basic=CLASS_FEATS_SW in feat_list,
                           feat_dict=CLASS_FEATS_DICT in feat_list,
                           posdict=pd,
                           output=feat_file)

    feat_file.close()
    EXTRACT_LOG.log(NORM_LEVEL, 'Written')



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

