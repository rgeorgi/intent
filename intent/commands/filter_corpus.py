from multiprocessing.pool import Pool
import os

from multiprocessing import Lock

from intent.igt.exceptions import NoNormLineException, MultipleNormLineException, EmptyGlossException, \
    GlossLangAlignException
from intent.igt.rgxigt import RGCorpus, sort_corpus, word_align
from intent.igt.igt_functions import lang, gloss, trans, pos_tags
from xigt.codecs import xigtxml
from xigt.consts import INCREMENTAL

__author__ = 'rgeorgi'

import logging
logging.getLogger()
FILTER_LOG = logging.getLogger('FILTERING')


def filter_corpus(filelist, outpath, require_lang=True, require_gloss=True, require_trans=True, require_aln=True, require_gloss_pos=False):
    new_corp = RGCorpus()


    FILTER_LOG.log(1000, "Beginning filtering...")

    successes = 0
    failures  = 0
    examined  = 0

    for path in filelist:
        FILTER_LOG.log(1000, 'Opening file "{}" for filtering.'.format(os.path.basename(path)))
        with open(path, 'r', encoding='utf-8') as f:
            xc = xigtxml.load(f, mode=INCREMENTAL)
            for inst in xc:
                examined += 1

                filter_string = 'Filter result for {:15s} {{:10s}}{{}}'.format(inst.id+':')

                def fail(reason):
                    nonlocal failures, filter_string
                    filter_string = filter_string.format("FAIL", '['+reason+']')
                    failures += 1
                    FILTER_LOG.info(filter_string)

                def success():
                    nonlocal successes, filter_string
                    filter_string = filter_string.format("SUCCESS", "")
                    successes += 1

                def trytier(f):
                    result = None
                    try:
                        result = f(inst)
                    except (NoNormLineException, MultipleNormLineException, EmptyGlossException) as mnle:
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
                    try:
                        word_align(gt, lt)
                    except GlossLangAlignException:
                        fail("ALIGN")
                        continue
                if require_gloss_pos:
                    if pos_tags(inst, gt.id) is None:
                        fail("GLOSS_POS")
                        continue

                # Otherwise, attach to the new corpus.
                new_corp.append(inst)

                success()
                FILTER_LOG.info(filter_string)

    try:
        os.makedirs(os.path.dirname(outpath))
    except (FileExistsError, FileNotFoundError) as fee:
        pass

    # Only create a file if there are some instances to create...
    if len(new_corp) > 0:

        with open(outpath, 'w', encoding='utf-8') as out_f:
            FILTER_LOG.log(1000, "{} instances processed, {} filtered out, {} remain.".format(examined, failures, successes))
            sort_corpus(new_corp)
            FILTER_LOG.log(1000, 'Writing remaining instances to file "{}"...'.format(os.path.basename(outpath)))
            xigtxml.dump(out_f, new_corp)
            FILTER_LOG.log(1000, "Success.")


    else:
        print("No instances remain after filtering. Skipping.")