"""
This module is used to run experiments for reproduction of
the results in the dissertation.
"""
import intent.commands.enrich
from intent.commands.filter import filter_corpus
from intent.interfaces import condor
from intent.consts import *
from intent.utils.env import *

# -------------------------------------------
# SET UP LOGGING
# -------------------------------------------
import logging

logging.addLevelName(NORM_LEVEL, 'NORMAL')
logging.basicConfig(level=NORM_LEVEL)
REPRO_LOG = logging.getLogger('REPRO')
# -------------------------------------------

class ExperimentFiles(object):

    def __init__(self, langs):
        self.langs = langs

    def _d(self, name, condor=False):
        p = os.path.join(exp_dir, name)
        if condor:
            p = os.path.join(p, 'condor')
        return p

    def _filter_dir(self, condor=False):
        return self._d('filtered', condor)

    def _enriched_dir(self, condor=False):
        return self._d('enriched', condor)

    def _tagged_dir(self, condor=False):
        return self._d('tagged', condor)

    def _tagger_dir(self, condor=False):
        return self._d('taggers', condor)

    def _parser_dir(self, condor=False):
        return self._d('parsers', condor)

    def orig(self, lang):
        return os.path.join(odin_xigt_dir, '{}.xml'.format(lang))

    def _f(self, format, dir, *args, condor=False):
        basename = format.format(*args)
        if condor:
            return basename
        else:
            return os.path.join(dir, basename+'.xml')

    def filtered(self, lang, condor=False):
        return self._f('{}_filtered', self._filter_dir(), lang, condor=condor)

    def enriched(self, lang, condor=False):
        return self._f('{}_enriched', self._enriched_dir(), lang, condor=condor)

    def projected(self, lang, align):
        return self._f('{}_proj_{}', self._tagged_dir(), lang, align, condor=condor)

    def classified(self, lang, cls):
        return self._f('{}_class_{}', self._tagged_dir(), lang, cls, condor=condor)


# -------------------------------------------
# Submit a python script to condor.
# -------------------------------------------
def condorify(args, prefix, name):
    p3path = which('python3')
    condor.run_cmd([p3path, intent_script] + args,
                   prefix=prefix, name=name, email=False)

# =============================================================================
# THE ENRICHMENT SCRIPTS
# =============================================================================

# -------------------------------------------
# FILTER
# -------------------------------------------

def filter(ef: ExperimentFiles, overwrite = False):
    """
    Filter all of the desired languages for the experiment.
    """
    filtration_performed = False

    # Iterate over all the languages.
    for lang in ef.langs:
        orig_path = ef.orig(lang)
        filt_path = ef.filtered(lang)

        # Don't overwrite already existing files unless
        # we've been asked to overwrite.
        if not os.path.exists(filt_path) or overwrite:

            if not filtration_performed:
                REPRO_LOG.log(NORM_LEVEL, "Filtering ODIN data.")

            if not USE_CONDOR:
                filter_corpus([orig_path], filt_path,
                              require_aln=True,
                              require_lang=True,
                              require_gloss=True,
                              require_trans=True)
            else:
                REPRO_LOG.log(NORM_LEVEL, "Filtering {}...".format(lang))
                args = ['filter',
                        '--require-aln',
                        '--require-lang',
                        '--require-gloss',
                        '--require-trans',
                        orig_path, filt_path]
                condorify(args, ef._filter_dir(condor=True), ef.filtered(lang, True))

            filtration_performed = True

    # If we're using condor, wait until all the
    # tasks for this step have completed.
    if USE_CONDOR and filtration_performed:
        if condor_email:
            condor.condor_wait_notify('Filtering of languages performed.', condor_email, "Filtration Done")
        else:
            condor.condor_wait()

    if filtration_performed:
        REPRO_LOG.log(NORM_LEVEL, "Filtration complete.")

# -------------------------------------------
# ENRICH
# -------------------------------------------

def enrich(ef: ExperimentFiles, overwrite = False, parse=False):
    """
    Enrich the files using all types of word alignment, and tag/parse the translation line.
    """
    pos_methods = [ARG_POS_PROJ, ARG_POS_CLASS]
    aln_methods = ARG_ALN_METHODS



    enrichment_performed = False
    for lang in ef.langs:

        filtered_f = ef.filtered(lang)
        enriched_f = ef.enriched(lang)

        if not os.path.exists(enriched_f) or overwrite:

            # Notify user of enrichment if at least one file is being enriched.
            if not enrichment_performed:
                REPRO_LOG.log(NORM_LEVEL, "Enriching ODIN data.")

            if not USE_CONDOR:
                enrich_args = ['']
                intent.commands.enrich.enrich()
            else:
                args = ['enrich',
                        '--align', 'heur,heurpos,giza,gizaheur',
                        '--pos', 'trans',
                        filtered_f, enriched_f]
                if parse:
                    args += ['--parse', 'trans']

                condorify(args, ef._filter_dir(condor=True), ef.filtered(lang, True))

            enrichment_performed = True

    if USE_CONDOR and enrichment_performed:
        if condor_email:
            condor.condor_wait_notify('Enrichment of languages performed.', condor_email, "Enrichment Done")
        else:
            condor.condor_wait()

    if enrichment_performed:
        REPRO_LOG.log(NORM_LEVEL, "Enrichment complete.")

# -------------------------------------------
# TAG
# -------------------------------------------

def postag(ef: ExperimentFiles, overwrite=False):
    tagging_performed = False
    for lang in ef.langs:
        pass

# =============================================================================
# Now to the main execution.
# =============================================================================

def reproduce(action):
    """
    :param action:
    """

    # ef = ExperimentFiles(['spa'])
    # filter(ef)
    # enrich(ef)


    # =============================================================================
    # POS (IGT) Reproduction
    # =============================================================================
    if action == REPRO_POS_IGT:
        pass


    # =============================================================================
    # POS (Mono) Repro
    # =============================================================================
    elif action == REPRO_POS_MONO:
        pass

    # =============================================================================
    # DS Reproduction
    # =============================================================================
    elif action == REPRO_DS:
        pass

