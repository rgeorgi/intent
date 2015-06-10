from collections import defaultdict
from glob import glob
import os
from intent.igt.rgxigt import RGCorpus
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.scripts.basic.split_corpus import split_instances
from intent.scripts.evaluation import evaluate_classifier_on_instances
from intent.scripts.extraction import extract_from_instances
from intent.utils.dicts import POSEvalDict
from intent.utils.env import tagger_model


def nfold_xaml():
    xaml_paths = glob("/Users/rgeorgi/Documents/code/dissertation/data/annotation/filtered/*.xml")

    lang_test = {}
    lang_train = {}
    lang_all  = {}

    tagger = StanfordPOSTagger(tagger_model)


    for xaml_path in xaml_paths:
        lang = os.path.basename(xaml_path)[:3]
        xc = RGCorpus.load(xaml_path)

        train, dev, test = split_instances(xc, train=0.5, test=0.5, dev=0.0)

        lang_train[lang] = train
        lang_all[lang] = train+test
        lang_test[lang] = test

    # Now, build our classifiers...

    all_other = POSEvalDict()
    all_all   = POSEvalDict()
    all_odin  = POSEvalDict()
    all_proj  = POSEvalDict()

    for lang in lang_all.keys():

        other_lang_instances = []
        all_lang_instances   = lang_train[lang]

        for other_lang in lang_all.keys():
            if other_lang != lang:
                other_lang_instances.extend(lang_all[other_lang])
                all_lang_instances.extend(lang_all[other_lang])

        other_lang_classifier = extract_from_instances(other_lang_instances, 'test.class', 'test.feats', '/dev/null')
        all_lang_classifier = extract_from_instances(all_lang_instances, 'all.class', 'all.feats', '/dev/null')


        test_instances = lang_test[lang]

        print(lang)
        prj_other_eval, cls_other_eval = evaluate_classifier_on_instances(test_instances, other_lang_classifier, tagger)
        prj_all_eval, cls_all_eval = evaluate_classifier_on_instances(test_instances, all_lang_classifier, tagger)
        prj_odin_eval, cls_odin_eval = evaluate_classifier_on_instances(test_instances, MalletMaxent('/Users/rgeorgi/Documents/code/dissertation/gc.classifier'), tagger)

        all_other += cls_other_eval
        all_all   += cls_all_eval
        all_odin  += cls_odin_eval
        all_proj  += prj_all_eval

    print('ALL')
    print('{:.2f},{:.2f},{:.2f},{:.2f},{:.2f}'.format(all_proj.precision(), all_proj.unaligned(), all_other.accuracy(), all_all.accuracy(), all_odin.accuracy()))
    print(all_proj.error_matrix(csv=True))




nfold_xaml()