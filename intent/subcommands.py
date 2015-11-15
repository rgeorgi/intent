"""
Created on Mar 24, 2015

@author: rgeorgi
"""

import sys
import logging
from io import StringIO

from intent.igt.consts import INTENT_POS_CLASS, INTENT_POS_PROJ, ODIN_GLOSS_TAG, ODIN_LANG_TAG, ODIN_TRANS_TAG
from intent.igt.rgxigt import RGCorpus, GlossLangAlignException,\
    PhraseStructureProjectionException, ProjectionException,\
    ProjectionTransGlossException, word_align, retrieve_normal_line, NoNormLineException, MultipleNormLineException

from intent.utils.arg_consts import PARSE_VAR, PARSE_TRANS, POS_VAR, ALN_VAR, POS_LANG_CLASS, ALN_HEUR, \
    ALN_GIZA, POS_LANG_PROJ, PARSE_LANG_PROJ, POS_TRANS
from intent.utils.env import c, posdict, odin_data
from intent.utils.argutils import writefile
from intent.interfaces.stanford_tagger import StanfordPOSTagger, TaggerError, CriticalTaggerError
from intent.interfaces.giza import GizaAlignmentException
from intent.interfaces import mallet_maxent, stanford_parser


# XIGT imports -----------------------------------------------------------------
from xigt.codecs import xigtxml
from intent.scripts.igt.extract_lang import extract_lang
from intent.scripts.conversion.odin_to_xigt import parse_text

#===============================================================================
# The ODIN subcommand
#===============================================================================

def odin(**kwargs):
    ODIN_LOG = logging.getLogger('ODIN')

    odin_txt = StringIO()
    print('Extracting languages matching "%s" from ODIN.' % kwargs.get('LNG'))
    extract_lang(odin_data, kwargs.get('LNG'), odin_txt, limit=kwargs.get('limit'))
    odin_txt_data = odin_txt.getvalue()

    print(kwargs.get('out_file'))

    if kwargs.get('format') == 'txt':
        f = open(kwargs.get('OUT_FILE'), 'w', encoding='utf-8')
        f.write(odin_txt_data)
    else:
        f = open(kwargs.get('OUT_FILE'), 'w', encoding='utf-8')

        parse_text(StringIO(odin_txt_data), f)


#===============================================================================
# The ENRICH subcommand.
#===============================================================================

def enrich(**kwargs):

    ENRICH_LOG = logging.getLogger('ENRICH')

    # =============================================================================
    # Set up the alternate classifier path...
    # =============================================================================
    if kwargs.get('class_path'):
        classifier = kwargs.get('class_path')

    #===========================================================================
    # Set up the different arguments...
    #===========================================================================
    inpath = kwargs.get('IN_FILE')

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


    print('Loading input file...')
    corp = RGCorpus.load(inpath, basic_processing=True)

    print("{} instances loaded...".format(len(corp)))

    #===========================================================================
    # If the tagger is asked for, initialize it.
    #===========================================================================
    if POS_LANG_PROJ in pos_args or POS_TRANS in pos_args:
        print('Initializing tagger...')
        tagger = c.getpath('stanford_tagger_trans')

        try:
            s = StanfordPOSTagger(tagger)
        except TaggerError:
            sys.exit(2)

    #===========================================================================
    # Initialize the parser
    #===========================================================================
    if PARSE_TRANS in parse_args:
        print("Intializing English parser...")
        sp = stanford_parser.StanfordParser()

    #===========================================================================
    # If the classifier is asked for, initialize it...
    #===========================================================================
    if POS_LANG_CLASS in pos_args:
        print("Initializing gloss-line classifier...")
        p = posdict
        m = mallet_maxent.MalletMaxent(classifier)

    # -- 1a) Heuristic Alignment --------------------------------------------------
    if ALN_HEUR in aln_args:
        print('Heuristically aligning gloss and translation lines...')
        corp.heur_align()

    # -- 1b) Giza Gloss to Translation alignment --------------------------------------
    if ALN_GIZA in aln_args:
        print('Aligning gloss and translation lines using mgiza++...')

        try:
            corp.giza_align_t_g(resume=True)
        except GizaAlignmentException as gae:
            gl = logging.getLogger('giza')
            gl.critical(str(gae))
            sys.exit(2)

    # -- 2) Iterate through the corpus -----------------------------------------------
    for inst in corp:

        try:
            has_gloss = True
            has_trans = True
            has_lang  = True

            has_all = lambda: (has_gloss and has_trans and has_lang)

            # -- A) Language Lines
            try:
                n = retrieve_normal_line(inst, ODIN_LANG_TAG)
                has_lang = n.value() is not None and n.value().strip()
            except (NoNormLineException, MultipleNormLineException) as e:
                has_lang = False

            # -- B) Gloss Lines
            try:
                n = retrieve_normal_line(inst, ODIN_GLOSS_TAG)
                has_gloss = n.value() is not None and n.value().strip()
            except (NoNormLineException, MultipleNormLineException) as e:
                has_gloss = False

            # -- C) Trans Lines
            try:
                n = retrieve_normal_line(inst, ODIN_TRANS_TAG)
                has_trans = n.value() is not None and n.value().strip()
            except (NoNormLineException, MultipleNormLineException) as e:
                has_trans = False


            # Attempt to align the gloss and language lines if requested... --------
            if has_gloss and has_lang:
                try:
                    word_align(inst.gloss, inst.lang)
                except GlossLangAlignException as glae:
                    ENRICH_LOG.warn(str(glae))
                except MultipleNormLineException as mnle:
                    pass # This will be errored out elsewhere...


            # 3) POS tag the translation line --------------------------------------
            if POS_LANG_PROJ in pos_args and has_trans:
                try:
                    inst.tag_trans_pos(s)
                except CriticalTaggerError as cte:
                    ENRICH_LOG.critical(str(cte))
                    sys.exit(2)
                except MultipleNormLineException as mnle:
                    ENRICH_LOG.warn(str(mnle) + ' Not projecting POS tags.')


            # 4) POS tag the gloss line --------------------------------------------
            if POS_LANG_CLASS in pos_args and has_gloss and has_lang:
                inst.classify_gloss_pos(m, posdict=p)
                try:
                    inst.project_gloss_to_lang(tag_method=INTENT_POS_CLASS)
                except GlossLangAlignException:
                    ENRICH_LOG.warning('The gloss and language lines for instance id "{}" do not align. Language line not POS tagged.'.format(inst.id))

            if POS_LANG_PROJ in pos_args and has_all():
                pos_tags = inst.get_pos_tags(inst.trans.id)
                aln = inst.get_trans_gloss_alignment()
                if not pos_tags:
                    ENRICH_LOG.warn('No trans-line POS tags available for "{}". Not projecting POS tags from trans line.'.format(inst.id))
                elif not aln:
                    ENRICH_LOG.warn('No trans-gloss alignment available for "{}". Not projecting POS tags from trans line.'.format(inst.id))
                else:
                    try:
                        inst.project_trans_to_gloss()
                    except ProjectionTransGlossException as ptge:
                        ENRICH_LOG.warning('No alignment between translation and gloss lines found for instance "%s". Not projecting POS tags.' % inst.id)
                    except ProjectionException as pe:
                        ENRICH_LOG.warning('No translation POS tags were found for instance "%s". Not projecting POS tags.' % inst.id)
                    else:
                        try:
                            inst.project_gloss_to_lang(tag_method=INTENT_POS_PROJ)
                        except GlossLangAlignException as glae:
                            ENRICH_LOG.warn(glae)


            # 5) Parse the translation line ----------------------------------------
            if PARSE_TRANS in parse_args and has_trans:
                # try:
                inst.parse_translation_line(sp, pt=True, dt=True)
                # except Exception as ve:
                    # pass
                    # ENRICH_LOG.critical("Unknown parse error in instance {}".format(inst1.id))
                    # ENRICH_LOG.critical(str(ve))

            # If parse tree projection is enabled... -------------------------------
            if PARSE_LANG_PROJ in parse_args and has_all():
                aln = inst.get_trans_gloss_lang_alignment()

                # If there's no alignment, just skip.
                if len(aln) == 0:
                    ENRICH_LOG.warning('No alignment available for "{}". Not projecting trees.'.format(inst.id))

                # If there's alignment, try projecting.
                else:
                    try:
                        inst.project_pt()
                    except PhraseStructureProjectionException as pspe:
                        ENRICH_LOG.warning('A parse for the translation line was not found for instance "%s", not projecting phrase structure.' % inst.id)
                    except ProjectionTransGlossException as ptge:
                        ENRICH_LOG.warning('Alignment between translation and gloss lines was not found for instance "%s". Not projecting phrase structure.' % inst.id)

                    try:
                        inst.project_ds()
                    except ProjectionException as pe:
                        ENRICH_LOG.warning(pe)


            # Sort the tiers... ----------------------------------------------------
            inst.sort()
        # except Exception as e:
        #     raise e

        except Exception as e:
            ENRICH_LOG.warn("Unknown Error occurred processing instance {}".format(inst.id))
            ENRICH_LOG.warn(e)

    print('Writing output file...', end=' ')
    xigtxml.dump(writefile(kwargs.get('OUT_FILE')), corp)
    print('Done.')
    print("{} instances written.".format(len(corp)))