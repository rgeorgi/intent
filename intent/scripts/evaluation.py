import os
from collections import defaultdict


from intent.consts import *
from intent.eval.AlignEval import AlignEval
from intent.eval.pos_eval import poseval
from intent.igt.rgxigt import RGCorpus, RGIgt
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.utils.dicts import POSEvalDict
from intent.utils.env import tagger_model, classifier
from intent.utils.token import POSToken

__author__ = 'rgeorgi'

import logging
EVAL_LOG = logging.getLogger('EVAL')


def evaluate_intent(filelist, classifier_path=None, eval_alignment=None):
    """
    Given a list of files that have manual POS tags and manual alignment,
    evaluate the various INTENT methods on that file.

    :param filelist: List of paths to evaluate against.
    :type filelist: list[str]
    :param classifier_path: Path to the classifier model
    :type classifier_path: str
    :param eval_alignment:
    """
    tagger = StanfordPOSTagger(tagger_model)

    # =============================================================================
    # Set up the objects to run as "servers"
    # =============================================================================

    classifier_obj = MalletMaxent(classifier)

    if classifier_path is not None:
        classifier_obj = MalletMaxent(classifier_path)


    overall_prj = POSEvalDict()
    overall_cls = POSEvalDict()

    mas = MultAlignScorer()

    # Go through all the files in the list...
    for f in filelist:
        print('Evaluating on file: {}'.format(f))
        xc = RGCorpus.load(f)

        # Test the classifier if evaluation is requested.
        if classifier_path is not None:
            prj_eval, cls_eval = evaluate_classifier_on_instances(xc, classifier, tagger)

            overall_prj += prj_eval
            overall_cls += cls_eval

        # Test alignment if requested.

        if eval_alignment:
            # evaluate_heuristic_methods_on_file(f, xc, mas, classifier_obj, tagger)
            evaluate_statistic_methods_on_file(f, xc, mas, classifier_obj, tagger)

    mas.eval_all()
    # Report the POS tagging accuracy...
    if classifier_path is not None:
        print("ALL...")
        print('{:.2f},{:.2f}'.format(overall_prj.accuracy(), overall_cls.accuracy()))

class MultAlignScorer(object):

    def __init__(self):
        self.by_lang_dict = defaultdict(lambda: defaultdict(list))
        self.methods = []

    def add_alignment(self, method, lang, aln):
        self.by_lang_dict[lang][method].append(aln)

        if method != 'gold' and method not in self.methods:
            self.methods.append(method)

    def add_corpus(self, name, method, lang, xc):
        """
        :type method: str
        :type xc: RGCorpus
        """
        for inst in xc:
            gold = inst.get_trans_gloss_alignment(aln_method=ARG_ALN_MANUAL)
            if gold is None:
                continue
            else:
                aln = inst.get_trans_gloss_alignment(aln_method=method)
                self.add_alignment(name, lang, aln)

    def eval_all(self):
        overall_dict = defaultdict(list)

        for method in self.methods:
            overall_dict[method] = AlignEval()


        for lang in self.by_lang_dict.keys():

            for method in self.methods:
                test_snts = self.by_lang_dict[lang][method]
                gold_snts = self.by_lang_dict[lang]['gold']
                ae = AlignEval(test_snts, gold_snts)
                print(','.join([lang,method]+[str(i) for i in ae.all()]))

                overall_dict[method] += ae

        for method in self.methods:
            print(','.join(['overall',method]+[str(i) for i in overall_dict[method].all()]))


def evaluate_heuristic_methods_on_file(f, xc, mas, classifier_obj, tagger_obj):
    EVAL_LOG.info('Evaluating heuristic methods on file "{}"'.format(os.path.basename(f)))

    manual_alignments = []
    heur_alignments = []

    for inst in xc:

        # -------------------------------------------
        # Only evaluate against instances that have a gold alignment.
        manual = inst.get_trans_gloss_alignment(aln_method=INTENT_ALN_MANUAL)
        if not manual:
            continue

        lang = os.path.basename(f)

        mas.add_alignment('gold', lang, manual)

        # heur = inst.heur_align(lowercase=True, stem=True, tokenize=True, no_multiples=False, use_pos=True)
        heur = inst.copy().heur_align(lowercase=False, stem=False, tokenize=False, no_multiples=True, use_pos=False)
        mas.add_alignment('baseline', lang, heur)

        heur = inst.copy().heur_align(lowercase=True, stem=False, tokenize=False, no_multiples=True, use_pos=False)
        mas.add_alignment('lowercasing', lang, heur)

        heur = inst.copy().heur_align(lowercase=True, stem=False, tokenize=True, no_multiples=True, use_pos=False)
        mas.add_alignment('Tokenization', lang, heur)

        heur = inst.copy().heur_align(lowercase=True, stem=False, tokenize=True, no_multiples=False, use_pos=False)
        mas.add_alignment('Multiple Matches', lang, heur)

        heur = inst.copy().heur_align(lowercase=True, stem=True, tokenize=True, no_multiples=False, use_pos=False)
        mas.add_alignment('Morphing', lang, heur)

        heur = inst.copy().heur_align(lowercase=True, stem=True, tokenize=True, no_multiples=False, grams=True, use_pos=False)
        mas.add_alignment('Grams', lang, heur)

        b = inst.copy()
        b.classify_gloss_pos(classifier_obj)
        b.tag_trans_pos(tagger_obj)
        heur = b.heur_align(lowercase=True, stem=True, tokenize=True, no_multiples=False, grams=True, use_pos=True)
        mas.add_alignment('POS', lang, heur)

        



        # inst.heur_align(stem=False)
        # inst.heur_align(tokenize=False)
        # inst.heur_align(no_multiples=True)
        # heur = inst.get_trans_gloss_alignment(INTENT_ALN_HEUR)

def evaluate_statistic_methods_on_file(f, xc, mas, classifier_obj, tagger):
    """
    :type xc: RGCorpus
    :type mas: MultAlignScorer
    """

    xc.heur_align()

    # Start by adding the manual alignments...
    mas.add_corpus('gold', INTENT_ALN_MANUAL, f, xc)

    EVAL_LOG.info("")
    xc.giza_align_t_g(aligner=ALIGNER_FASTALIGN, use_heur=False)
    mas.add_corpus('fast_align', INTENT_ALN_GIZA, f, xc)
    xc.remove_alignments(INTENT_ALN_GIZA)

    xc.giza_align_t_g(aligner=ALIGNER_FASTALIGN, use_heur=True)
    mas.add_corpus('fast_align_heur', INTENT_ALN_GIZA, f, xc)
    xc.remove_alignments(INTENT_ALN_GIZA)

    xc.giza_align_t_g(use_heur=False, resume=False)
    mas.add_corpus('statistic', INTENT_ALN_GIZA, f, xc)
    xc.remove_alignments(INTENT_ALN_GIZA)

    xc.giza_align_t_g(use_heur=True, resume=False)
    mas.add_corpus('statistic_heur', INTENT_ALN_GIZA, f, xc)
    xc.remove_alignments(INTENT_ALN_GIZA)

    xc.giza_align_t_g(use_heur=False, resume=True)
    mas.add_corpus('statistic+', INTENT_ALN_GIZA, f, xc)
    xc.remove_alignments(INTENT_ALN_GIZA)

    xc.giza_align_t_g(use_heur=True, resume=True)
    mas.add_corpus('statistic+_heur', INTENT_ALN_GIZA, f, xc)
    xc.remove_alignments(INTENT_ALN_GIZA)



# =============================================================================
# Evaluate instances
#
# This is just to
# =============================================================================
def evaluate_instance(inst, classifier, tagger):
    # Get the supervised POS tags...
    """

    :param inst:
    :type inst: RGIgt
    :param classifier: MalletMaxent
    :param tagger: StanfordPOSTagger
    """
    sup_gloss_tier = inst.get_pos_tags(GLOSS_WORD_ID)  # We will incrementally build up the tag sequences...
    sup_lang_tier  = inst.get_pos_tags(LANG_WORD_ID)
    sup_tags = []
    prj_tags = []
    cls_tags = []

    # If there are no supervised tags on the gloss line, but there are on the language line...
    if sup_gloss_tier is None and sup_lang_tier is not None:
        inst.add_gloss_lang_alignments()
        inst.project_lang_to_gloss()
        sup_gloss_tier = inst.get_pos_tags(GLOSS_WORD_ID)

    if sup_gloss_tier:

        # Do the classification
        inst.classify_gloss_pos(classifier)

        # Do the projection...
        inst.heur_align()
        inst.tag_trans_pos(tagger)

        inst.project_trans_to_gloss(aln_method=INTENT_ALN_HEUR, tag_source=INTENT_POS_TAGGER)

        # Now, go through each aligned ID for the supervised tags, and match them with those in the other
        # tiers... IF they exist.

        prj_tier = inst.get_pos_tags(GLOSS_WORD_ID, tag_method=INTENT_POS_PROJ)
        cls_tier = inst.get_pos_tags(GLOSS_WORD_ID, tag_method=INTENT_POS_CLASS)

        for sup_item in sup_gloss_tier:
            word = inst.find(id=sup_item.alignment)
            if not word:
                continue
            else:
                word = word.value()

            prj_item = prj_tier.find(alignment=sup_item.alignment)
            if prj_item is None:
                prj_tag = 'UNK'
            else:
                prj_tag = prj_item.value()

            cls_item = cls_tier.find(alignment=sup_item.alignment)
            if cls_item is None:
                cls_tag = 'UNK'
            else:
                cls_tag = cls_item.value()

            sup_tags.append(POSToken(word, label=sup_item.value()))
            prj_tags.append(POSToken(word, label=prj_tag))
            cls_tags.append(POSToken(word, label=cls_tag))

    return sup_tags, prj_tags, cls_tags


def evaluate_classifier_on_instances(inst_list, classifier, tagger):
    """
    Given a list of instances, do the evaluation on them.

    :param inst_list:
    :param classifier:
    :param tagger:
    :return:
    """
    sup_sents, prj_sents, cls_sents = [], [], []

    for inst in inst_list:
        sup_tags, prj_tags, cls_tags = evaluate_instance(inst.copy(), classifier, tagger)

        sup_sents.append(sup_tags)
        prj_sents.append(prj_tags)
        cls_sents.append(cls_tags)

    prj_eval = poseval(prj_sents, sup_sents, out_f=open('/dev/null', 'w'))
    cls_eval = poseval(cls_sents, sup_sents, out_f=open('/dev/null', 'w'))

    print('{:.2f},{:.2f},{:.2f}'.format(prj_eval.accuracy(), prj_eval.unaligned(), cls_eval.accuracy()))
    print(prj_eval.error_matrix())

    return prj_eval, cls_eval
