import logging
import sys

from intent.consts import *
from intent.igt.create_tiers import gloss_line, trans_lines, lang_lines, trans_tag_tier
from intent.igt.exceptions import GlossLangAlignException, PhraseStructureProjectionException, \
    ProjectionException, NoNormLineException
from intent.igt.igt_functions import giza_align_t_g, tag_trans_pos, parse_translation_line, classify_gloss_pos, \
    word_align, heur_align_inst, project_gloss_pos_to_lang, get_trans_gloss_alignment, project_trans_pos_to_gloss, \
    project_pt_tier, project_ds_tier, add_gloss_lang_alignments
from intent.interfaces import mallet_maxent, stanford_parser
from intent.interfaces.giza import GizaAlignmentException
from intent.interfaces.stanford_tagger import StanfordPOSTagger, TaggerError, CriticalTaggerError
from intent.trees import NoAlignmentProvidedError
from intent.utils.argutils import writefile
from intent.utils.env import c, posdict, classifier, load_posdict
from xigt.codecs import xigtxml

ENRICH_LOG = logging.getLogger('ENRICH')

#===============================================================================
# The ENRICH subcommand.
#===============================================================================
from xigt.consts import INCREMENTAL


def enrich_instance(**kwargs):
    pass

def enrich(class_path=None, **kwargs):



    if ARG_OUTFILE not in kwargs:
        ENRICH_LOG.critical("No output file specified.")
        sys.exit()

    # =============================================================================
    # Set up the alternate classifier path...
    # =============================================================================

    if class_path:
        classifier_path = mallet_maxent.MalletMaxent(class_path)

    #===========================================================================
    # Set up the different arguments...
    #===========================================================================
    inpath = kwargs.get(ARG_INFILE)

    parse_args = kwargs.get(PARSE_VAR, [])
    pos_args = kwargs.get(POS_VAR, [])
    aln_args = kwargs.get(ALN_VAR, [])

    if not (parse_args or pos_args or aln_args):
        ENRICH_LOG.warning("No enrichment specified. Basic processing only will be performed.")

    #===========================================================================
    # Sanity check the arguments.
    #===========================================================================

    # Check that alignment is asked for if projection is asked for.
    if (ARG_POS_PROJ in pos_args or ARG_PARSE_PROJ in parse_args) and (not aln_args):
        ENRICH_LOG.warn("You have asked for projection methods but have not requested " + \
                        "alignments to be generated. Projection may fail if alignment not already present in file.")

    ENRICH_LOG.log(1000, 'Loading input file...')
    with open(inpath, 'r', encoding='utf-8') as in_f:
        corp = xigtxml.load(in_f, mode=INCREMENTAL)

        # -------------------------------------------
        # Initialize the English tagger if:
        #   A) "proj" option is selected for pos.
        #   B) "trans" option is given for pos.
        #   C) "heurpos" option is given for alignment.
        # -------------------------------------------
        s = None
        if ARG_POS_PROJ in pos_args or ARG_POS_TRANS in pos_args or ARG_ALN_HEURPOS in aln_args:
            ENRICH_LOG.log(1000, 'Initializing tagger...')
            tagger = c.getpath('stanford_tagger_trans')

            try:
                s = StanfordPOSTagger(tagger)
            except TaggerError:
                sys.exit(2)

        # -------------------------------------------
        # Initialize the parser if:
        #    A) "trans" option is given for parse
        #    B) "proj" option is given for parse.
        # -------------------------------------------
        if ARG_PARSE_TRANS in parse_args or ARG_PARSE_PROJ in parse_args:
            ENRICH_LOG.log(1000, "Intializing English parser...")
            sp = stanford_parser.StanfordParser()

        # -------------------------------------------
        # Initialize the classifier if:
        #    A) "class" option is given for pos
        #    B) "heurpos" option is given for alignment.
        # -------------------------------------------
        m = None
        if ARG_POS_CLASS in pos_args or ARG_ALN_HEURPOS in aln_args:
            ENRICH_LOG.log(1000, "Initializing gloss-line classifier...")
            p = load_posdict()
            m = mallet_maxent.MalletMaxent(classifier)


        # -- 1b) Giza Gloss to Translation alignment --------------------------------------
        if ARG_ALN_GIZA in aln_args or ARG_ALN_GIZAHEUR in aln_args:
            ENRICH_LOG.log(1000, 'Aligning gloss and translation lines using mgiza++...')

            try:
                if ARG_ALN_GIZAHEUR in aln_args:
                    giza_align_t_g(corp, resume=True, use_heur=True, symmetric=kwargs.get(ALN_SYM_VAR))
                if ARG_ALN_GIZA in aln_args:
                    giza_align_t_g(corp, resume=True, use_heur=False, symmetric=kwargs.get(ALN_SYM_VAR))
            except GizaAlignmentException as gae:
                gl = logging.getLogger('giza')
                gl.critical(str(gae))
                sys.exit(2)

        # -------------------------------------------
        # Begin iterating through the corpus
        # -------------------------------------------

        for inst in corp:

            feedback_string = 'Instance {:15s}: {{:20s}}{{}}'.format(inst.id)

            reasons = []
            inst_status = None

            def fail(reason):
                nonlocal inst_status, reasons
                if reason not in reasons:
                    reasons.append(reason)
                inst_status = 'WARN'

            def success():
                nonlocal inst_status
                inst_status = 'OK'

            # -------------------------------------------
            # Define the reasons for failure
            # -------------------------------------------
            F_GLOSS_LINE = "NOGLOSS"
            F_LANG_LINE  = "NOLANG"
            F_TRANS_LINE = "NOTRANS"
            F_BAD_LINES  = "BADLINES"
            F_L_G_ALN    = "L_G_ALIGN"
            F_T_G_ALN    = "G_T_ALIGN"
            F_NO_TRANS_POS="NO_POS_TRANS"
            F_PROJECTION = "PROJECTION"
            F_UNKNOWN    = "UNKNOWN"


            try:

                # -------------------------------------------
                # Get the different lines
                # -------------------------------------------
                def tryline(func):
                    nonlocal inst
                    try:
                        return func(inst)
                    except NoNormLineException as nnle:
                        return None

                gl = tryline(gloss_line)
                tls = tryline(trans_lines)
                lls  = tryline(lang_lines)

                has_gl = gl is not None
                has_tl = tls is not None
                has_ll = lls is not None

                has_all = lambda: (has_gl and has_tl and has_ll)


                # -------------------------------------------
                # Translation Line
                # -------------------------------------------
                if has_tl:

                    if ARG_POS_PROJ in pos_args or ARG_POS_TRANS in pos_args or ARG_ALN_HEURPOS in aln_args:

                        try:
                            tag_trans_pos(inst, s)
                        except CriticalTaggerError as cte:
                            ENRICH_LOG.critical(str(cte))
                            sys.exit(2)

                    if ARG_PARSE_PROJ in parse_args or ARG_PARSE_TRANS in parse_args:
                        parse_translation_line(inst, sp, pt=True, dt=True)

                # 4) POS tag the gloss line --------------------------------------------
                if has_gl:
                    if ARG_POS_CLASS in pos_args or ARG_ALN_HEURPOS in aln_args:
                        classify_gloss_pos(inst, m, posdict=p)

                # -------------------------------------------
                # Try getting alignments.
                # -------------------------------------------
                if has_gl and has_ll:
                    try:
                        add_gloss_lang_alignments(inst)
                    except GlossLangAlignException as glae:
                        fail(F_L_G_ALN)

                if has_gl and has_tl:
                    if ARG_ALN_HEURPOS in aln_args:
                        heur_align_inst(inst, use_pos=True)
                    if ARG_ALN_HEUR in aln_args:
                        heur_align_inst(inst, use_pos=False)

                # -------------------------------------------
                # Now, do the necessary projection tasks.
                # -------------------------------------------

                # Project the classifier tags...
                if has_ll and has_gl and ARG_POS_CLASS in pos_args:
                    try:
                        project_gloss_pos_to_lang(inst, tag_method=INTENT_POS_CLASS)
                    except GlossLangAlignException:
                        fail(F_L_G_ALN)

                # -------------------------------------------
                # Do the trans-to-lang projection...
                # -------------------------------------------

                if has_all():
                    proj_aln_method = ALN_ARG_MAP[kwargs.get('proj_aln', ARG_ALN_ANY)]
                    aln = get_trans_gloss_alignment(inst, aln_method=proj_aln_method)
                    if not aln or len(aln) == 0:
                        fail(F_T_G_ALN)
                    else:
                        # -------------------------------------------
                        # POS Projection
                        # -------------------------------------------
                        if ARG_POS_PROJ in pos_args:
                            trans_tags = trans_tag_tier(inst)

                            if not trans_tags:
                                fail(F_NO_TRANS_POS)
                            else:
                                project_trans_pos_to_gloss(inst)
                                try:
                                    project_gloss_pos_to_lang(inst, tag_method=INTENT_POS_PROJ)
                                except GlossLangAlignException as glae:
                                    fail(F_L_G_ALN)

                        # -------------------------------------------
                        # Parse projection
                        # -------------------------------------------
                        if ARG_PARSE_PROJ in parse_args:
                            try:
                                project_pt_tier(inst, proj_aln_method=proj_aln_method)
                            except PhraseStructureProjectionException as pspe:
                                fail(F_PROJECTION)
                            except NoAlignmentProvidedError as nape:
                                fail(F_T_G_ALN)

                            try:
                                project_ds_tier(inst, proj_aln_method=proj_aln_method)
                            except ProjectionException as pe:
                                fail(F_PROJECTION)
                            except NoAlignmentProvidedError as nape:
                                fail(F_T_G_ALN)



                # Sort the tiers... ----------------------------------------------------
                inst.sort_tiers()

            except Exception as e:
                # ENRICH_LOG.warn("Unknown Error occurred processing instance {}".format(inst.id))
                ENRICH_LOG.debug(e)
                # raise(e)
                fail(F_UNKNOWN)

            if not reasons:
                success()


            ENRICH_LOG.info(feedback_string.format(inst_status, ','.join(reasons)))

        ENRICH_LOG.log(1000, 'Writing output file...')

        if hasattr(kwargs.get(ARG_OUTFILE), 'write'):
            xigtxml.dump(kwargs.get(ARG_OUTFILE), corp)
        else:
            xigtxml.dump(writefile(kwargs.get(ARG_OUTFILE)), corp)

        ENRICH_LOG.log(1000, 'Done.')
        ENRICH_LOG.log(1000, "{} instances written.".format(len(corp)))

