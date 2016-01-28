import logging
import sys

from intent.consts import *
from intent.interfaces import mallet_maxent, stanford_parser
from intent.interfaces.giza import GizaAlignmentException
from intent.interfaces.stanford_tagger import StanfordPOSTagger, TaggerError, CriticalTaggerError
from intent.utils.argutils import writefile
from intent.utils.env import c, posdict, classifier
from xigt.codecs import xigtxml

#===============================================================================
# The ENRICH subcommand.
#===============================================================================
from xigt.consts import INCREMENTAL


def enrich(**kwargs):

    ENRICH_LOG = logging.getLogger('ENRICH')

    if 'OUT_FILE' not in kwargs:
        ENRICH_LOG.critical("No output file specified.")
        sys.exit()

    # =============================================================================
    # Set up the alternate classifier path...
    # =============================================================================

    if kwargs.get('class_path'):
        classifier_path = mallet_maxent.MalletMaxent(kwargs.get('class_path'))

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
    if (POS_LANG_PROJ in pos_args or PARSE_LANG_PROJ in parse_args) and (not aln_args):
        ENRICH_LOG.warn("You have asked for projection methods but have not requested " + \
                        "alignments to be generated. Projection may fail if alignment not already present in file.")

    ENRICH_LOG.log(1000, 'Loading input file...')
    corp = RGCorpus.load(inpath, basic_processing=True, mode=INCREMENTAL)

    ENRICH_LOG.log(1000, "{} instances loaded...".format(len(corp)))

    # -------------------------------------------
    # Initialize the English tagger if:
    #   A) "proj" option is selected for pos.
    #   B) "trans" option is given for pos.
    #   C) "heurpos" option is given for alignment.
    # -------------------------------------------
    s = None
    if POS_LANG_PROJ in pos_args or POS_TRANS in pos_args or ARG_ALN_HEURPOS in aln_args:
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
    if PARSE_TRANS in parse_args or PARSE_LANG_PROJ in parse_args:
        ENRICH_LOG.log(1000, "Intializing English parser...")
        sp = stanford_parser.StanfordParser()

    # -------------------------------------------
    # Initialize the classifier if:
    #    A) "class" option is given for pos
    #    B) "heurpos" option is given for alignment.
    # -------------------------------------------
    m = None
    if POS_LANG_CLASS in pos_args or ARG_ALN_HEURPOS in aln_args:
        ENRICH_LOG.log(1000, "Initializing gloss-line classifier...")
        p = posdict
        m = mallet_maxent.MalletMaxent(classifier)


    # -- 1b) Giza Gloss to Translation alignment --------------------------------------
    if ARG_ALN_GIZA in aln_args or ARG_ALN_GIZAHEUR in aln_args:
        ENRICH_LOG.log(1000, 'Aligning gloss and translation lines using mgiza++...')

        try:
            if ARG_ALN_GIZAHEUR in aln_args:
                corp.giza_align_t_g(resume=True, use_heur=True, symmetric=kwargs.get(ALN_SYM_VAR))
            if ARG_ALN_GIZA in aln_args:
                corp.giza_align_t_g(resume=True, use_heur=False, symmetric=kwargs.get(ALN_SYM_VAR))
        except GizaAlignmentException as gae:
            gl = logging.getLogger('giza')
            gl.critical(str(gae))
            sys.exit(2)

    # -------------------------------------------
    # Begin iterating through the corpus
    # -------------------------------------------

    for inst in corp:

        try:

            # -------------------------------------------
            # Get the different lines
            # -------------------------------------------
            gl = gloss_line(inst)
            tl = trans_line(inst)
            ll  = lang_line(inst)

            has_gl = gl is not None
            has_tl = tl is not None
            has_ll = ll is not None

            has_all = lambda: (has_gl and has_tl and has_ll)


            # -------------------------------------------
            # Translation Line
            # -------------------------------------------
            if has_tl:

                if POS_LANG_PROJ in pos_args or POS_TRANS in pos_args or ARG_ALN_HEURPOS in aln_args:

                    try:
                        inst.tag_trans_pos(s)
                    except CriticalTaggerError as cte:
                        ENRICH_LOG.critical(str(cte))
                        sys.exit(2)

                if PARSE_LANG_PROJ in parse_args or PARSE_TRANS in parse_args:
                    inst.parse_translation_line(sp, pt=True, dt=True)

            # 4) POS tag the gloss line --------------------------------------------
            if has_gl:
                if POS_LANG_CLASS in pos_args or ARG_ALN_HEURPOS in aln_args:
                    inst.classify_gloss_pos(m, posdict=p)

            # -------------------------------------------
            # Try getting alignments.
            # -------------------------------------------
            if has_gl and has_ll:
                try:
                    word_align(inst.gloss, inst.lang)
                except GlossLangAlignException as glae:
                    ENRICH_LOG.warn(str(glae))
                except MultipleNormLineException as mnle:
                    pass # This will be errored out elsewhere...

            if has_gl and has_tl:
                if ARG_ALN_HEURPOS in aln_args:
                    inst.heur_align(use_pos=True)
                if ARG_ALN_HEUR in aln_args:
                    inst.heur_align(use_pos=False)

            # -------------------------------------------
            # Now, do the necessary projection tasks.
            # -------------------------------------------

            # Project the classifier tags...
            if has_ll and has_gl and POS_LANG_CLASS in pos_args:
                try:
                    inst.project_gloss_to_lang(tag_method=INTENT_POS_CLASS)
                except GlossLangAlignException:
                    pass

            # -------------------------------------------
            # Do the trans-to-lang projection...
            # -------------------------------------------

            if has_all():
                proj_aln_method = ALN_ARG_MAP[kwargs.get('proj_aln', ARG_ALN_ANY)]
                aln = get_trans_gloss_alignment(inst, aln_method=proj_aln_method)
                if not aln or len(aln) == 0:
                    ENRICH_LOG.warning("No alignment found between translation and gloss for instance {}, no projection will be done.".format(inst.id))
                else:
                    # -------------------------------------------
                    # POS Projection
                    # -------------------------------------------
                    if POS_LANG_PROJ in pos_args:
                        pos_tags = inst.get_pos_tags(inst.trans.id)

                        if not pos_tags:
                            ENRICH_LOG.warn('No trans-line POS tags available for "{}". Not projecting POS tags from trans line.'.format(inst.id))
                        else:
                            inst.project_trans_to_gloss()
                            try:
                                inst.project_gloss_to_lang(tag_method=INTENT_POS_PROJ)
                            except GlossLangAlignException as glae:
                                pass

                    # -------------------------------------------
                    # Parse projection
                    # -------------------------------------------
                    if PARSE_LANG_PROJ in parse_args:
                        try:
                            project_pt_tier(inst, proj_aln_method=proj_aln_method)
                        except PhraseStructureProjectionException as pspe:
                            ENRICH_LOG.warning(pspe)

                        try:
                            project_ds_tier(inst, proj_aln_method=proj_aln_method)
                        except ProjectionException as pe:
                            ENRICH_LOG.warning(pe)


            # Sort the tiers... ----------------------------------------------------
            inst.sort_tiers()

        except Exception as e:
            ENRICH_LOG.warn("Unknown Error occurred processing instance {}".format(inst.id))
            ENRICH_LOG.warn(e)
            raise(e)

    ENRICH_LOG.log(1000, 'Writing output file...')

    if hasattr(kwargs.get(ARG_OUTFILE), 'write'):
        xigtxml.dump(kwargs.get(ARG_OUTFILE), corp)
    else:
        xigtxml.dump(writefile(kwargs.get(ARG_OUTFILE)), corp)

    ENRICH_LOG.log(1000, 'Done.')
    ENRICH_LOG.log(1000, "{} instances written.".format(len(corp)))

from intent.igt.rgxigt import RGCorpus, GlossLangAlignException,\
    PhraseStructureProjectionException, ProjectionException, \
    word_align, MultipleNormLineException
from intent.igt.search import *
from intent.igt.projection import project_pt_tier, project_ds_tier