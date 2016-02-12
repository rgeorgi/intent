# -------------------------------------------
# (Re)do POS and parse projection from a file that
# already has alignment and
# -------------------------------------------
import logging
import os

import sys

from intent.igt.create_tiers import gloss, lang
from intent.igt.references import xigt_findall
from intent.utils.argpasser import ArgPasser

PROJ_LOG = logging.getLogger("REPROJECT")

from intent.igt.exceptions import NoNormLineException, ProjectionException, GlossLangAlignException, \
    ProjectionIncompleteAlignment
from intent.igt.igt_functions import project_trans_pos_to_gloss, \
    project_gloss_pos_to_lang, project_pt_tier, project_ds_tier, delete_tier
from intent.trees import NoAlignmentProvidedError
from xigt.codecs import xigtxml

from intent.consts import *
from xigt.consts import INCREMENTAL


def do_projection(**kwargs):
    """
    (Re)project the
    :param aln_method: The alignment method
    """
    kwargs = ArgPasser(kwargs)
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

            # Query whether we want to require to use only trees
            # where the alignment is 100%.
            completeness_requirement = kwargs.get('completeness', default=0, t=float)

            try:
                # Start by removing previous info...
                try:
                    gpos_tiers = xigt_findall(inst, alignment=gloss(inst).id, type=POS_TIER_TYPE)
                    lpos_tiers = xigt_findall(inst, alignment=lang(inst).id, type=POS_TIER_TYPE)
                    for gt in gpos_tiers:
                        delete_tier(gt)
                    for lt in lpos_tiers:
                        delete_tier(lt)

                except NoNormLineException:
                    pass

                project_trans_pos_to_gloss(inst, aln_method=aln_method, completeness_requirement=completeness_requirement)
                project_gloss_pos_to_lang(inst, tag_method=INTENT_POS_PROJ)
                project_pt_tier(inst, proj_aln_method=aln_method)
                project_ds_tier(inst, proj_aln_method=aln_method, completeness_requirement=completeness_requirement)
            except (NoNormLineException) as ntle:
                fail("Bad Lines")
            except (NoAlignmentProvidedError, ProjectionException) as nape:
                fail("Alignment")
            except (GlossLangAlignException) as glae:
                fail("Gloss-Lang")
            except (ProjectionIncompleteAlignment) as pia:
                fail("Alignment Incomplete")
            else:
                success()
            finally:
                PROJ_LOG.info(success_fail_string)
                inst.sort_tiers()

        out_path = kwargs.get(ARG_OUTFILE)
        # Try to make the folder if it doesn't already exist.
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        PROJ_LOG.log(1000, 'Writing new file "{}"...'.format(os.path.basename(out_path)))
        with open(out_path, 'w', encoding='utf-8') as out_f:
            xigtxml.dump(out_f, xc)

    PROJ_LOG.log(1000, '{} instances processed, {} successful, {} failed.'.format(len(xc), successes, failures))