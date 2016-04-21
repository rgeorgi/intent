import os, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from multiprocessing.pool import Pool

from multiprocessing import Lock
import threading

import time

from nltk.tag import pos_tag_sents

from intent.consts import NORM_LEVEL, ARG_ALN_MANUAL, INTENT_ALN_MANUAL, INTENT_ALN_GIZA, ALIGNER_FASTALIGN, \
    GLOSS_WORD_ID, LANG_WORD_ID, INTENT_ALN_HEUR, INTENT_POS_TAGGER, INTENT_POS_PROJ, INTENT_POS_CLASS, \
    INTENT_ALN_GIZAHEUR, ALIGNER_GIZA, INTENT_DS_MANUAL, INTENT_DS_PARSER, INTENT_DS_PROJ, INTENT_ALN_HEURPOS, \
    INTENT_POS_MANUAL
from intent.igt.exceptions import GlossLangAlignException, RGXigtException
from intent.igt.igtutils import rgp
from intent.igt.metadata import get_intent_method, set_intent_method

from intent.igt.parsing import xc_load


from intent.eval.AlignEval import AlignEval
from intent.eval.pos_eval import poseval
from intent.igt.igt_functions import heur_align_corp, giza_align_t_g, remove_alignments, copy_xigt, heur_align_inst, \
    classify_gloss_pos, tag_trans_pos, get_trans_gloss_lang_alignment, get_trans_gloss_alignment, giza_align_l_t, \
    get_trans_lang_alignment, get_bilingual_alignment_tier, add_gloss_lang_alignments, tier_alignment, get_lang_ds, \
    parse_translation_line, project_ds_tier, project_trans_pos_to_gloss, project_lang_to_gloss
from intent.igt.create_tiers import trans, gloss, gloss_tag_tier, glosses, pos_tag_tier, lang_tag_tier, trans_tag_tier
from intent.igt.references import xigt_find
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.trees import TreeProjectionError
from intent.utils.dicts import POSEvalDict
from intent.utils.env import tagger_model, classifier
from intent.utils.listutils import flatten_list
from intent.utils.token import POSToken
from xigt.codecs import xigtxml
from xigt.consts import INCREMENTAL, FULL
from xigt.model import XigtCorpus

__author__ = 'rgeorgi'

import logging
EVAL_LOG = logging.getLogger('EVAL')

def evaluate_intent(filelist, classifier_path=None, eval_alignment=None, eval_ds=None, eval_posproj=None):
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
    ds_plma = PerLangMethodAccuracies()
    pos_plma= PerLangMethodAccuracies()

    # Go through all the files in the list...
    for f in filelist:
        print('Evaluating on file: {}'.format(f))
        xc = xc_load(f, mode=FULL)
        lang = os.path.basename(f)

        # -------------------------------------------
        # Test the classifier if evaluation is requested.
        # -------------------------------------------
        if classifier_path is not None:
            prj_eval, cls_eval = evaluate_classifier_on_instances(xc, classifier_obj, tagger)

            overall_prj += prj_eval
            overall_cls += cls_eval

        # -------------------------------------------
        # Test alignment if requested.
        # -------------------------------------------
        if eval_alignment:
            mas.add_corpus('gold', INTENT_ALN_MANUAL, lang, xc)
            EVAL_LOG.log(NORM_LEVEL, "Evaluating heuristic methods...")
            evaluate_heuristic_methods_on_file(f, xc, mas, classifier_obj, tagger, lang)

            EVAL_LOG.log(NORM_LEVEL, "Evaluating statistical methods...")
            evaluate_statistic_methods_on_file(f, xc, mas, classifier_obj, tagger, lang)

        # -------------------------------------------
        # Test DS Projection if requested
        # -------------------------------------------
        if eval_ds:
            evaluate_ds_projections_on_file(lang, xc, ds_plma)
            print(ds_plma)

        # -------------------------------------------
        #  Test POS Projection
        # -------------------------------------------
        if eval_posproj:
            evaluate_pos_projections_on_file(lang, xc, pos_plma, tagger)



    if eval_alignment:
        mas.eval_all()

    if eval_ds:
        print(ds_plma)

    # Report the POS tagging accuracy...
    if classifier_path is not None:
        print("ALL...")
        print('{:.2f},{:.2f},{:.2f}'.format(overall_prj.accuracy(), overall_prj.unaligned(), overall_cls.accuracy()))

def evaluate_pos_projections_on_file(lang, xc, plma, tagger):
    """
    :type plma: PerLangMethodAccuracies
    """
    new_xc = XigtCorpus(xc.id)
    for inst in xc:

        gtt = gloss_tag_tier(inst, INTENT_POS_MANUAL)
        ttt = trans_tag_tier(inst, INTENT_POS_MANUAL)
        m_aln = get_trans_gloss_alignment(inst, INTENT_ALN_MANUAL)

        # Only continue if we have manual gloss tags, trans tags, and manual alignment.
        if gtt is None or m_aln is None or ttt is None:
            continue

        # Get the heuristic alignment...
        h_aln = heur_align_inst(inst)

        # And tag the translation line.
        tag_trans_pos(inst, tagger=tagger)

        # Now, iterate through each alignment method and set of tags.
        for aln_method in [INTENT_ALN_MANUAL, INTENT_ALN_HEUR]:
            for trans_tag_method in [INTENT_POS_MANUAL, INTENT_POS_TAGGER]:
                project_trans_pos_to_gloss(inst, aln_method=aln_method, trans_tag_method=trans_tag_method)
                proj_gtt = gloss_tag_tier(inst, tag_method=INTENT_POS_PROJ)

                # Go through each word in the gloss line and, if it has a gold
                # tag, was it correct?
                matches = 0
                compares = 0
                for gw in gloss(inst):
                    gold_tag = xigt_find(gtt, alignment=gw.id)
                    proj_tag = xigt_find(proj_gtt, alignment=gw.id)

                    if gold_tag is not None:
                        if proj_tag is not None and proj_tag.value() == gold_tag.value():
                            matches += 1
                        compares += 1


                plma.add(lang, '{}:{}'.format(aln_method, trans_tag_method), matches, compares)

    print(plma)





    return new_xc

def evaluate_ds_projections_on_file(lang, xc, plma):
    """
    :type plma: PerLangMethodAccuracies
    """
    matches    = 0
    compares   = 0

    aln_methods=[INTENT_ALN_GIZA, INTENT_ALN_GIZAHEUR, INTENT_ALN_HEUR, INTENT_ALN_HEURPOS, INTENT_ALN_MANUAL]

    for inst in xc:
        # giza_align_t_g(inst)

        gold_ds = get_lang_ds(inst, parse_method=INTENT_DS_MANUAL)
        if not gold_ds:
            continue

        # -------------------------------------------
        # If we have a gold standard DS, let's continue.
        # -------------------------------------------
        def eval_method(aln_method):

            # Set up the gold instances
            gold_edges = set(gold_ds.to_indices())
            # Add the number of compares, (the gold edges)
            # and currently 0 for matches...
            plma.add(lang, aln_method, 0, len(gold_edges))

            # Try to do the projection
            try:
                project_ds_tier(inst, proj_aln_method=aln_method, ds_source=INTENT_DS_PARSER)
                ds = get_lang_ds(inst, parse_method=INTENT_DS_PROJ)
                tgt_edges  = set(ds.to_indices())
                # Add the number of matches, with 0 compares, since we added
                # those previously.
                plma.add(lang, aln_method, len(gold_edges & tgt_edges), 0)

            except TreeProjectionError:
                pass

        for aln_method in aln_methods:
            eval_method(aln_method)


class PerMethodAccuracies(object):
    def __init__(self):
        self._dict = defaultdict(lambda: {'matches':0, 'compares':0})

    def add_match(self, m, n=1):
        self._dict[m]['matches'] += n

    def add_compare(self, m, n=1):
        self._dict[m]['compares'] += n

    def add(self, method, matches, compares):
        self.add_match(method, matches)
        self.add_compare(method, compares)

    def __add__(self, other):
        for m in set(self._dict.keys())|set(other._dict.keys()):
            self._dict[m]['matches'] += other._dict[m]['matches']
            self._dict[m]['compares'] += other._dict[m]['compares']

    def matches(self, m):
        return self._dict[m]['matches']

    def compares(self, m):
        return self._dict[m]['compares']

    def acc(self, m):
        return self.matches(m)/ self.compares(m) * 100

    def keys(self):
        return self._dict.keys()

    def __str__(self):
        accs = ['{:.2f}'.format(self.acc(m)) for m in self._dict.keys()]
        return ','.join(accs)

class PerLangMethodAccuracies(object):
    def __init__(self):
        self._mdict = defaultdict(lambda: PerMethodAccuracies())
        self._methods = []

    def add(self, lang, method, matches, compares):
        self._mdict[lang].add(method, matches, compares)
        if method not in self._methods:
            self._methods.append(method)

    def lang_acc(self, lang, m):
        return self._mdict[lang].acc(m)

    def overall_acc(self, m):
        matches = 0
        compares = 0
        for lang in self._mdict.keys():
            matches  += self._mdict[lang].matches(m)
            compares += self._mdict[lang].compares(m)
        return matches/compares * 100

    def __add__(self, other):
        for lang in set(self._mdict.keys()|other._mdict.keys()):
            self._mdict[lang] += other._mdict[lang]

    def __str__(self):
        ret_str = self.header_str()+'\n'
        for lang in sorted(self._mdict.keys()):
            accs = ['{:.2f}'.format(self._mdict[lang].acc(m)) for m in self._methods]
            for method in self._methods:
                acc = self._mdict[lang].acc(method)
            ret_str += ','.join([lang]+accs)+'\n'

        overall_accs = ['{:.2f}'.format(self.overall_acc(m)) for m in self._methods]
        ret_str += ','.join(['overall']+overall_accs)+'\n'
        return ret_str

    def header_str(self):
        return ','.join(['lang']+self._methods)


class MultAlignScorer(object):

    def __init__(self):
        self.by_lang_dict = defaultdict(lambda: defaultdict(dict))
        self.methods = []

    def add_alignment(self, method, lang, snt_id, aln):
        self.by_lang_dict[lang][method][snt_id] = aln

        if method != 'gold' and method not in self.methods:
            self.methods.append(method)

    def add_corpus(self, name, method, lang, xc, lang_trans = False):
        """
        :type method: str
        :type xc: RGCorpus
        """
        for inst in xc:
            # -------------------------------------------
            # Only continue when there is a gold standard
            # alignment to compare against.
            # -------------------------------------------
            gold = get_trans_gloss_alignment(inst, aln_method=ARG_ALN_MANUAL)
            if gold is None:
                continue

            if lang_trans:
                aln = get_trans_lang_alignment(inst, aln_method=method)
            else:
                aln = get_trans_gloss_alignment(inst, aln_method=method)

            self.add_alignment(name, lang, inst.id, aln)

    def eval_all(self):
        overall_dict = defaultdict(list)

        for method in self.methods:
            overall_dict[method] = AlignEval()


        for lang in self.by_lang_dict.keys():

            for method in self.methods:
                test_snts = []
                gold_snts = []

                for snt_id in self.by_lang_dict[lang][method].keys():
                    test_snt = self.by_lang_dict[lang][method][snt_id]
                    gold_snt = self.by_lang_dict[lang]['gold'][snt_id]
                    test_snts.append(test_snt)
                    gold_snts.append(gold_snt)

                try:
                    ae = AlignEval(test_snts, gold_snts)
                except AssertionError as ae:
                    print("ERROR IN METHOD {}".format(method))
                    raise(ae)
                print(','.join([lang,method]+[str(i) for i in ae.all()]))

                overall_dict[method] += ae

        for method in self.methods:
            print(','.join(['overall',method]+[str(i) for i in overall_dict[method].all()]))


def evaluate_heuristic_methods_on_file(f, xc, mas, classifier_obj, tagger_obj, lang, pool=None, lock=None):
    EVAL_LOG.info('Evaluating heuristic methods on file "{}"'.format(os.path.basename(f)))




    for inst in xc:

        # -------------------------------------------
        # Only evaluate against instances that have a gold alignment.
        manual = get_trans_gloss_alignment(inst, aln_method=INTENT_ALN_MANUAL)

        if manual is None:
            continue

        EVAL_LOG.debug('Running heuristic alignments on instance "{}"'.format(inst.id))

        heur = heur_align_inst(copy_xigt(inst), lowercase=False, stem=False, tokenize=False, no_multiples=True, use_pos=False)
        mas.add_alignment('baseline', lang, inst.id, heur)

        heur = heur_align_inst(copy_xigt(inst), lowercase=True, stem=False, tokenize=False, no_multiples=True, use_pos=False)
        mas.add_alignment('lowercasing', lang, inst.id, heur)

        heur = heur_align_inst(copy_xigt(inst), lowercase=True, stem=False, tokenize=True, no_multiples=True, use_pos=False)
        mas.add_alignment('Tokenization', lang, inst.id, heur)

        heur = heur_align_inst(copy_xigt(inst), lowercase=True, stem=False, tokenize=True, no_multiples=False, use_pos=False)
        mas.add_alignment('Multiple Matches', lang, inst.id, heur)

        heur = heur_align_inst(copy_xigt(inst), lowercase=True, stem=True, tokenize=True, no_multiples=False, use_pos=False)
        mas.add_alignment('Morphing', lang, inst.id, heur)

        heur = heur_align_inst(copy_xigt(inst), lowercase=True, stem=True, tokenize=True, no_multiples=False, grams=True, use_pos=False)
        mas.add_alignment('Grams', lang, inst.id, heur)


        b = copy_xigt(inst)
        classify_gloss_pos(b, classifier_obj)
        tag_trans_pos(b, tagger_obj)
        heur = heur_align_inst(b, lowercase=True, stem=True, tokenize=True, no_multiples=False, grams=True, use_pos=True)
        mas.add_alignment('POS', lang, inst.id, heur)



def evaluate_statistic_methods_on_file(f, xc, mas, classifier_obj, tagger, lang, pool=None, lock=None):
    """
    :type xc: RGCorpus
    :type mas: MultAlignScorer
    """
    heur_align_corp(xc)

    giza_align_l_t(xc)
    mas.add_corpus('lang_trans', INTENT_ALN_GIZA, lang, xc, lang_trans=True)
    remove_alignments(xc, INTENT_ALN_GIZA)

    giza_align_l_t(xc, use_heur=True)
    mas.add_corpus('lang_trans_heur', INTENT_ALN_GIZA, lang, xc, lang_trans=True)
    remove_alignments(xc, INTENT_ALN_GIZA)

    giza_align_t_g(xc, aligner=ALIGNER_FASTALIGN, use_heur=False)
    mas.add_corpus('fast_align', INTENT_ALN_GIZA, lang, xc)
    remove_alignments(xc, INTENT_ALN_GIZA)

    giza_align_t_g(xc, aligner=ALIGNER_FASTALIGN, use_heur=True)
    mas.add_corpus('fast_align_heur', INTENT_ALN_GIZAHEUR, lang, xc)
    remove_alignments(xc, INTENT_ALN_GIZAHEUR)

    giza_align_t_g(xc, use_heur=False, resume=False)
    mas.add_corpus('statistic', INTENT_ALN_GIZA, lang, xc)
    remove_alignments(xc, INTENT_ALN_GIZA)

    giza_align_t_g(xc, use_heur=True, resume=False)
    mas.add_corpus('statistic_heur', INTENT_ALN_GIZAHEUR, lang, xc)
    remove_alignments(xc, INTENT_ALN_GIZAHEUR)

    giza_align_t_g(xc, use_heur=False, resume=True)
    mas.add_corpus('statistic+', INTENT_ALN_GIZA, lang, xc)
    remove_alignments(xc, INTENT_ALN_GIZA)

    giza_align_t_g(xc, use_heur=True, resume=True)
    mas.add_corpus('statistic+_heur', INTENT_ALN_GIZAHEUR, lang, xc)
    remove_alignments(xc, INTENT_ALN_GIZAHEUR)



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
    sup_gloss_tier = pos_tag_tier(inst, GLOSS_WORD_ID)  # We will incrementally build up the tag sequences...
    sup_lang_tier  = pos_tag_tier(inst, LANG_WORD_ID)


    sup_tags = []
    prj_tags = []
    cls_tags = []

    # If there are no supervised tags on the gloss line, but there are on the language line...
    if sup_gloss_tier is None and sup_lang_tier is not None:
        try:
            add_gloss_lang_alignments(inst)
            project_lang_to_gloss(inst)
            sup_gloss_tier = pos_tag_tier(inst, GLOSS_WORD_ID)
        except RGXigtException:
            pass

    if sup_gloss_tier:

        # Do the classification
        classify_gloss_pos(inst, classifier)

        # Do the projection...
        heur_align_inst(inst)

        tag_trans_pos(inst, tagger)

        project_trans_pos_to_gloss(inst, aln_method=INTENT_ALN_HEUR, trans_tag_method=INTENT_POS_TAGGER)

        # Now, go through each aligned ID for the supervised tags, and match them with those in the other
        # tiers... IF they exist.

        prj_tier = pos_tag_tier(inst, GLOSS_WORD_ID, tag_method=INTENT_POS_PROJ)
        cls_tier = pos_tag_tier(inst, GLOSS_WORD_ID, tag_method=INTENT_POS_CLASS)

        for sup_item in sup_gloss_tier:
            word = xigt_find(inst, id=sup_item.alignment)
            if not word:
                continue
            else:
                word = word.value()

            prj_item = xigt_find(prj_tier, alignment=sup_item.alignment)
            if prj_item is None:
                prj_tag = 'UNK'
            else:
                prj_tag = prj_item.value()

            cls_item = xigt_find(cls_tier, alignment=sup_item.alignment)
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
        sup_tags, prj_tags, cls_tags = evaluate_instance(copy_xigt(inst), classifier, tagger)

        sup_sents.append(sup_tags)
        prj_sents.append(prj_tags)
        cls_sents.append(cls_tags)

    prj_eval = poseval(prj_sents, sup_sents, out_f=open('/dev/null', 'w'))
    cls_eval = poseval(cls_sents, sup_sents, out_f=open('/dev/null', 'w'))

    print('{:.2f},{:.2f},{:.2f}'.format(prj_eval.accuracy(), prj_eval.unaligned(), cls_eval.accuracy()))
    print(prj_eval.error_matrix())

    return prj_eval, cls_eval
