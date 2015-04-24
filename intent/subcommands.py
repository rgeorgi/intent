'''
Created on Mar 24, 2015

@author: rgeorgi
'''

import sys
import logging
from io import StringIO

from intent.igt.consts import INTENT_POS_CLASS, INTENT_POS_PROJ, ODIN_GLOSS_TAG, ODIN_LANG_TAG, ODIN_TRANS_TAG
from intent.igt.rgxigt import RGCorpus, GlossLangAlignException,\
    PhraseStructureProjectionException, ProjectionException,\
    ProjectionTransGlossException, word_align, MultipleNormLineException, retrieve_normal_line, NoNormLineException, \
    NoLangLineException, NoTransLineException, NoGlossLineException
from intent.utils.arg_consts import PARSE_VAR, PARSE_TRANS, POS_VAR, ALN_VAR, POS_LANG_CLASS, ALN_HEUR, \
    ALN_GIZA, POS_LANG_PROJ, PARSE_LANG_PROJ, POS_TRANS
from intent.utils.env import c, classifier, posdict, odin_data
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


    #===========================================================================
    # Set up the different arguments...
    #===========================================================================
    inpath = kwargs.get('IN_FILE')

    parse_args = kwargs.get(PARSE_VAR)
    pos_args = kwargs.get(POS_VAR)
    aln_args = kwargs.get(ALN_VAR)

    #===========================================================================
    # Sanity check the arguments.
    #===========================================================================

    # Check that alignment is asked for if projection is asked for.
    if POS_LANG_PROJ in pos_args or PARSE_LANG_PROJ in parse_args and not aln_args:
        ENRICH_LOG.warn("You have asked for projection methods but have not requested " + \
                        "alignments to be generated. Projection may fail if alignment not already present in file.")


    print('Loading input file...')
    corp = RGCorpus.load(inpath, basic_processing=True)

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
            corp.giza_align_t_g()
        except GizaAlignmentException as gae:
            gl = logging.getLogger('giza')
            gl.critical(str(gae))
            sys.exit(2)

    # -- 2) Iterate through the corpus -----------------------------------------------
    for inst in corp:

        # TODO: Clean up this exception handling?
        # Currently, just skip multiple normalized lines...
        try:
            retrieve_normal_line(inst, ODIN_LANG_TAG)
            retrieve_normal_line(inst, ODIN_GLOSS_TAG)
            retrieve_normal_line(inst, ODIN_TRANS_TAG)
        except MultipleNormLineException as mnle:
            ENRICH_LOG.warn(str(mnle))
            continue
        except (NoNormLineException, NoGlossLineException, NoTransLineException, NoLangLineException) as e:
            pass

        # Attempt to align the gloss and language lines if requested... --------
        try:
            word_align(inst.gloss, inst.lang)
        except GlossLangAlignException as glae:
            ENRICH_LOG.warn(str(glae))

        # 3) POS tag the translation line --------------------------------------
        if POS_LANG_CLASS in pos_args:
            try:
                inst.tag_trans_pos(s)
            except CriticalTaggerError as cte:
                ENRICH_LOG.critical(str(cte))
                sys.exit(2)

        # 4) POS tag the gloss line --------------------------------------------
        if POS_LANG_CLASS in pos_args:
            inst.classify_gloss_pos(m, posdict=p)
            try:
                inst.project_gloss_to_lang(tag_method=INTENT_POS_CLASS)
            except GlossLangAlignException:
                ENRICH_LOG.warning('The gloss and language lines for instance id "%s" do not align. Language line not POS tagged.' % inst.id)

        if POS_LANG_PROJ in pos_args:
            try:
                inst.project_trans_to_gloss()
            except ProjectionTransGlossException as ptge:
                ENRICH_LOG.warning('No alignment between translation and gloss lines found for instance "%s". Not projecting POS tags.' % inst.id)
            except ProjectionException as pe:
                ENRICH_LOG.warning('No translation POS tags were found for instance "%s". Not projecting POS tags.' % inst.id)
            else:
                inst.project_gloss_to_lang(tag_method=INTENT_POS_PROJ)


        # 5) Parse the translation line ----------------------------------------
        if PARSE_TRANS in parse_args:
            try:
                inst.parse_translation_line(sp, pt=True, dt=True)
            except Exception as ve:
                ENRICH_LOG.critical("Unknown parse error in instance {}".format(inst.id))
                ENRICH_LOG.critical(str(ve))

        # If parse tree projection is enabled... -------------------------------
        if PARSE_LANG_PROJ in parse_args:
            try:
                inst.project_pt()
            except PhraseStructureProjectionException as pspe:
                ENRICH_LOG.warning('A parse for the translation line was not found for instance "%s", not projecting phrase structure.' % inst.id)
            except ProjectionTransGlossException as ptge:
                ENRICH_LOG.warning('Alignment between translation and gloss lines was not found for instance "%s". Not projecting phrase structure.' % inst.id)
            except Exception as ie:
                ENRICH_LOG.critical("Unknown projection error in instance {}".format(inst.id))
                ENRICH_LOG.critical(str(ie))

        # Sort the tiers... ----------------------------------------------------
        inst.sort()


    print('Writing output file...', end=' ')
    xigtxml.dump(writefile(kwargs.get('OUT_FILE')), corp)
    print('Done.')