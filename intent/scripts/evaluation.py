import sys
from tempfile import NamedTemporaryFile
from intent.eval.pos_eval import poseval
from intent.igt.consts import GLOSS_WORD_ID, MANUAL_POS, INTENT_POS_PROJ, INTENT_POS_CLASS, INTENT_ALN_HEUR, \
    INTENT_POS_TAGGER
from intent.igt.igtutils import rgp
from intent.igt.rgxigt import RGCorpus, RGIgt, strip_pos
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.utils.dicts import TwoLevelCountDict, POSEvalDict
from intent.utils.env import tagger_model
from intent.utils.token import POSToken, GoldTagPOSToken
from xigt.consts import ALIGNMENT

__author__ = 'rgeorgi'

def evaluate_intent(filelist, classifier_path, eval_alignment):
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

    if classifier_path:
        classifier = MalletMaxent(classifier_path)

    overall_prj = POSEvalDict()
    overall_cls = POSEvalDict()

    # Go through all the files in the list...
    for f in filelist:
        print('Evaluating on file: {}'.format(f))
        xc = RGCorpus.load(f)

        prj_eval, cls_eval = evaluate_classifier_on_instances(xc, classifier, tagger)

        overall_prj += prj_eval
        overall_cls += cls_eval

    print("ALL...")
    print('{:.2f},{:.2f}'.format(overall_prj.accuracy(), overall_cls.accuracy()))

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
    sup_tier = inst.get_pos_tags(GLOSS_WORD_ID)  # We will incrementally build up the tag sequences...
    sup_tags = []
    prj_tags = []
    cls_tags = []

    if sup_tier:

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

        for sup_item in sup_tier:
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
