from multiprocessing.pool import Pool
import os

from intent.consts import NORM_LEVEL
from intent.igt.exceptions import NoNormLineException, EmptyGlossException, \
    GlossLangAlignException
from intent.igt.igt_functions import lang, gloss, trans, pos_tag_tier, word_align
from intent.igt.parsing import xc_load
from xigt import XigtCorpus, Igt
from xigt.codecs import xigtxml
from xigt.consts import INCREMENTAL

__author__ = 'rgeorgi'

import logging
logging.getLogger()
FILTER_LOG = logging.getLogger('FILTERING')

def filter_corpus(filelist, outpath, require_lang=False, require_gloss=False, require_trans=False, require_aln=False, require_gloss_pos=False):
    xc, examined, failures, successes = do_filter(filelist, require_lang, require_gloss, require_trans, require_aln, require_gloss_pos)

    # Only create a file if there are some instances to create...
    if len(xc) > 0:

        # Make sure the directory exists that contains the output.
        os.makedirs(os.path.dirname(outpath), exist_ok=True)

        with open(outpath, 'w', encoding='utf-8') as out_f:
            FILTER_LOG.log(1000, "{} instances processed, {} filtered out, {} remain.".format(examined, failures, successes))
            FILTER_LOG.log(1000, 'Writing remaining instances to file "{}"...'.format(os.path.basename(outpath)))
            xigtxml.dump(out_f, xc)
            FILTER_LOG.log(1000, "Success.")

    else:
        print("No instances remain after filtering. Skipping.")

def filter_string(inst):
    return 'Filter result for {:15s} {{:10s}}{{}}'.format(inst.id+':')


def filter_xc(xc, require_lang=False, require_gloss=False, require_trans=False, require_aln=False, require_gloss_pos=False):

    new_corp = XigtCorpus()

    examined = 0
    failures = 0
    successes= 0

    my_filter = ''

    for inst in xc:
        examined += 1
        assert isinstance(inst, Igt)

        def fail(reason):
            nonlocal failures, my_filter
            my_filter = filter_string(inst).format("FAIL", '['+reason+']')
            failures += 1
            FILTER_LOG.info(my_filter)

        def success():
            nonlocal successes, my_filter
            my_filter = filter_string(inst).format("SUCCESS", "")
            successes += 1


        def trytier(f):
            try:
                result = f(inst)
            except (NoNormLineException) as nnle:
                return None
                fail("Bad Lines")
            else:
                return result


        lt = trytier(lang)
        gt = trytier(gloss)
        tt = trytier(trans)


        if require_lang  and lt is None:
            fail("LANG")
            continue
        if require_gloss and gt is None:
            fail("GLOSS")
            continue
        if require_trans and tt is None:
            fail("TRANS")
            continue
        if require_aln:

            if gt is None:
                fail("ALIGN-GLOSS")
                continue
            if lt is None:
                fail("ALIGN-LANG")
                continue

            try:
                word_align(gt, lt)
            except GlossLangAlignException:
                fail("ALIGN")
                continue

        if require_gloss_pos:
            if pos_tag_tier(inst, gt.id) is None:
                fail("GLOSS_POS")
                continue

        # Otherwise, attach to the new corpus.
        new_corp.append(inst)

        success()
        FILTER_LOG.info(my_filter)
        inst.sort_tiers()

    return new_corp, examined, successes, failures

def do_filter(filelist, require_lang=False, require_gloss=False, require_trans=False, require_aln=False, require_gloss_pos=False):
    new_corp = XigtCorpus()

    FILTER_LOG.log(NORM_LEVEL, "Beginning filtering...")

    successes = 0
    failures  = 0
    examined  = 0

    for path in filelist:
        FILTER_LOG.log(1000, 'Opening file "{}" for filtering.'.format(os.path.basename(path)))
        xc = xc_load(path, mode=INCREMENTAL)
        instances, iter_examined, iter_success, iter_failures = filter_xc(xc, require_lang, require_gloss, require_trans, require_aln, require_gloss_pos)
        for instance in instances:
            new_corp.append(instance)

        successes += iter_success
        failures  += iter_failures
        examined  += iter_examined

    return new_corp, examined, failures, successes
