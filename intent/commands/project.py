# -------------------------------------------
# (Re)do POS and parse projection from a file that
# already has alignment and
# -------------------------------------------
import logging
import os

PROJ_LOG = logging.getLogger("REPROJECT")

from intent.igt.exceptions import NoTransLineException, NoNormLineException, MultipleNormLineException, \
    ProjectionException
from intent.igt.igt_functions import lang, gloss, get_bilingual_alignment, project_trans_pos_to_gloss, \
    project_gloss_pos_to_lang, project_pt_tier, project_ds_tier
from intent.trees import NoAlignmentProvidedError
from xigt.codecs import xigtxml

from intent.consts import *
from xigt.consts import INCREMENTAL


def do_projection(**kwargs):

    aln_method = ALN_ARG_MAP[kwargs.get('aln_method', ARG_ALN_ANY)]

    successes = 0
    failures  = 0



    in_path = kwargs.get(ARG_INFILE)
    with open(in_path, 'r', encoding='utf-8') as f:
        PROJ_LOG.log(1000, 'Loading file "{}"...'.format(os.path.basename(in_path)))
        xc = xigtxml.load(f, mode=INCREMENTAL)
        for inst in xc:
            success_fail_string = 'Instance {:20s} {{:10s}}{{}}'.format('"'+inst.id+'"...')

            def fail(reason):
                nonlocal failures, success_fail_string
                success_fail_string = success_fail_string.format('FAIL', reason)
                failures += 1
            def success():
                nonlocal successes, success_fail_string
                success_fail_string = success_fail_string.format('SUCCESS', '')
                successes += 1

            try:
                project_trans_pos_to_gloss(inst, aln_method=aln_method)
                project_gloss_pos_to_lang(inst, tag_method=INTENT_POS_PROJ)
                project_pt_tier(inst, proj_aln_method=aln_method)
                project_ds_tier(inst, proj_aln_method=aln_method)
            except (NoTransLineException, MultipleNormLineException) as ntle:
                fail("Bad Lines")
            except (NoAlignmentProvidedError, ProjectionException) as nape:
                fail("Alignment")
            else:
                success()
            finally:
                PROJ_LOG.info(success_fail_string)


        out_path = kwargs.get(ARG_OUTFILE)
        PROJ_LOG.log(1000, 'Writing new file "{}"...'.format(os.path.basename(out_path)))
        with open(out_path, 'w', encoding='utf-8') as out_f:
            xc.sort()
            xigtxml.dump(out_f, xc)

    PROJ_LOG.log(1000, '{} instances processed, {} successful, {} failed.'.format(len(xc), successes, failures))