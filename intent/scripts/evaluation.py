import sys
from tempfile import NamedTemporaryFile

from intent.eval.AlignEval import AlignEval
from intent.eval.pos_eval import poseval
from intent.igt.consts import GLOSS_WORD_ID, MANUAL_POS, INTENT_POS_PROJ, INTENT_POS_CLASS, INTENT_ALN_HEUR, \
    INTENT_POS_TAGGER, LANG_WORD_ID, INTENT_ALN_MANUAL, INTENT_ALN_GIZA
from intent.igt.igtutils import rgp
from intent.igt.rgxigt import RGCorpus, RGIgt, strip_pos
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.utils.arg_consts import ALN_MANUAL
from intent.utils.dicts import TwoLevelCountDict, POSEvalDict
from intent.utils.env import tagger_model, classifier
from intent.utils.token import POSToken, GoldTagPOSToken
from xigt.consts import ALIGNMENT

__author__ = 'rgeorgi'

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

    if classifier_path is not None:
        classifier = MalletMaxent(classifier_path)

    overall_prj = POSEvalDict()
    overall_cls = POSEvalDict()

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
            evaluate_alignment_on_file(xc)


    # Report the POS tagging accuracy...
    if classifier_path is not None:
        print("ALL...")
        print('{:.2f},{:.2f}'.format(overall_prj.accuracy(), overall_cls.accuracy()))

def evaluate_alignment_on_file(xc):
    """
    :type xc: RGCorpus
    """
    xc2 = xc.copy()

    xc.heur_align(use_pos=False)

    xc3 = xc.copy()

    xc3.giza_align_t_g(use_heur=True, resume=True)

    xc.giza_align_t_g(resume=True)


    xc2.giza_align_t_g(resume=False)

    sp = StanfordPOSTagger(tagger_model)
    mc = MalletMaxent(classifier)

    heur_alignments = []
    # heur_pos_alignments = []
    giza_alignments_aug = []
    giza_alignments_resume = []
    giza_alignments_fresh = []
    gold_alignments = []

    for inst, inst2, inst3 in zip(xc, xc2, xc3):

        assert isinstance(inst, RGIgt)
        assert isinstance(inst2, RGIgt)
        assert isinstance(inst3, RGIgt)

        manual      = inst.get_trans_gloss_alignment(aln_method=INTENT_ALN_MANUAL)
        giza_resume = inst.get_trans_gloss_alignment(aln_method=INTENT_ALN_GIZA)
        giza_fresh = inst2.get_trans_gloss_alignment(aln_method=INTENT_ALN_GIZA)
        giza_augment = inst3.get_trans_gloss_alignment(aln_method=INTENT_ALN_GIZA)

        heur        = inst.get_trans_gloss_alignment(aln_method=INTENT_ALN_HEUR)

        # inst2.classify_gloss_pos(mc)
        # inst2.tag_trans_pos(sp)
        # inst2.heur_align(use_pos=True)


        # heur_pos    = inst2.get_trans_gloss_alignment(aln_method=INTENT_ALN_HEUR)

        heur_alignments.append(heur)
        # heur_pos_alignments.append(heur_pos)
        gold_alignments.append(manual)
        giza_alignments_aug.append(giza_augment)
        giza_alignments_resume.append(giza_resume)
        giza_alignments_fresh.append(giza_fresh)

    heur_ae = AlignEval(heur_alignments, gold_alignments)
    # heur_pos_ae = AlignEval(heur_pos_alignments, gold_alignments)
    giza_augment_ae = AlignEval(giza_alignments_aug, gold_alignments)
    giza_resume_ae = AlignEval(giza_alignments_resume, gold_alignments)
    giza_fresh_ae  = AlignEval(giza_alignments_fresh, gold_alignments)

    print(AlignEval.header())
    # print(heur_pos_ae.all())
    print(heur_ae.all())

    print(giza_augment_ae.all())
    print(giza_resume_ae.all())
    print(giza_fresh_ae.all())


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
