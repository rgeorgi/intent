"""
This module is used to run experiments for reproduction of
the results in the dissertation.
"""
from collections import defaultdict
from functools import partial

import intent.commands.enrich
from intent.commands.extraction import extract_from_xigt
from intent.commands.filter import filter_corpus
from intent.commands.project import do_projection
from intent.commands.evaluation import evaluate_intent
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

# -------------------------------------------
# Setting up some methods
# -------------------------------------------
pos_methods = [ARG_POS_PROJ, ARG_POS_CLASS]
aln_methods = ARG_ALN_METHODS

completeness_list = [('all', 0.0), ('full',1.0)]
# -------------------------------------------
class SingleConfig(object):
    def __init__(self, ef, lang, method, *args):
        """
        :type ef: ExperimentFiles
        """
        self.ef = ef
        self.lang = lang
        self.method = method
        if method == ARG_POS_CLASS:
            self.c_name, self.c_path = args[0]
        elif method == ARG_POS_PROJ:
            self.complete_name, self.complete_ratio = args[0]
            self.aln_method = args[1]

    def __repr__(self):
        if self.method == ARG_POS_CLASS:
            return '<TagConfig: {},{},{}>'.format(self.lang, self.method, self.c_name)
        else:
            return '<TagConfig: {},{},{},{}>'.format(self.lang, self.method, self.aln_method, self.complete_name)

    def orig(self):
        return self.ef.orig(self.lang)

    def filtered(self):
        return self.ef.filtered(self.lang)

    def rgigt(self):
        return self.ef.rgigt(self.lang)

    def rgigt_eval(self):
        if self.method == ARG_POS_CLASS:
            return self.ef.rgigt_eval(self.lang, '{}_{}'.format(self.method, self.c_name))
        else:
            return self.ef.rgigt_eval(self.lang, '{}_{}_{}'.format(self.method, self.aln_method, self.complete_name))

    def enriched(self):
        return self.ef.enriched(self.lang)

    def tagged(self, condor=False):
        if self.method == ARG_POS_CLASS:
            return self.ef.classified(self.lang, self.c_name, condor=condor)
        else:
            return self.ef.projected(self.lang, self.aln_method, self.complete_name, condor=condor)

    def _tagger_path(self, prefix=False, name=False):
        if self.method == ARG_POS_CLASS:
            return self.ef.tagger(self.lang, self.method, self.c_name, prefix=prefix, name=name)
        else:
            return self.ef.tagger(self.lang, self.method, '{}_{}'.format(self.aln_method, self.complete_name), prefix=prefix, name=name)

    def tagger_path(self):
        return self._tagger_path(prefix=False, name=False)

    def tagger_name(self):
        return self._tagger_path(prefix=False, name=True)

    def tagger_prefix(self):
        return self._tagger_path(prefix=True, name=False)

    def tag_args(self, condor):
        """
        Return the appropriate arguments for the
        corresponding tagging process.
        """
        if self.method == ARG_POS_CLASS:
            if condor:
                return [['enrich', '--pos', 'class', '--class', self.c_path, self.filtered(), self.tagged()],
                        self.ef._tagged_dir(condor=True), self.tagged(condor=True)]
            else:
                return {ARG_INFILE: self.filtered(),
                        ARG_OUTFILE: self.tagged(),
                        POS_VAR: ARG_POS_CLASS,
                        'class_path': self.c_path}
        else:
            if condor:
                return [['project', '--aln-method', self.aln_method, '--completeness', self.complete_ratio, self.enriched(), self.tagged()],
                        self.ef._tagged_dir(condor=True), self.tagged(condor=True)]
            else:
                return {ARG_INFILE: self.filtered(),
                        ARG_OUTFILE: self.tagged(),
                        'aln_method':self.aln_method,
                        'completeness':self.complete_ratio}


    def extract_args(self, condor):
        """
        Return the appropriate arguments for the corresponding
        extraction process
        """
        if condor:
            args = [['extract', '--tagger-prefix', self.tagger_prefix(), '--use-pos', self.method, self.tagged()],
                    self.ef._tagger_dir(condor=True), self.tagger_name()]
            return args
        else:
            args = [[self.tagged], {'tagger_prefix':self.tagger_prefix(), 'pos_method':self.method}]
            return args

    def eval_igt_pos_args(self, condor):
        """
        Return the args for evaluating.
        """
        if condor:
            args = [['eval', '--pos-tagger', self.tagger_path(), '--output', self.rgigt_eval(), self.rgigt()],
                    self.ef._rgigt_eval_dir(True), self.tagger_name()]
            return args
        else:
            args = [[self.rgigt()],
                    {'eval_tagger':self.tagger_path(),
                     'outpath':self.rgigt_eval()}]
            return args

# =============================================================================
# EXPERIMENT FILES
# =============================================================================
lang_mapping = {'deu':'de',
                'spa':'es',
                'fra':'fr',
                'ind':'id',
                'ita':'it',
                'por':'pt-br',
                'swe':'sv'}

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

    def _rgigt_eval_dir(self, condor=False):
        return self._d('eval_igt_pos', condor)

    def _xligt_eval_dir(self, condor=False):
        return self._d('eval_igt_ds', condor)

    def _ud2_eval_dir(self, condor=False):
        return self._d('eval_mono_pos', condor)

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

    def tagger_configs(self):
        """
        :rtype: list[SingleConfig]
        """
        l = []
        for lang in self.langs:
            for class_pair in class_dict.items():
                tc = SingleConfig(self, lang, ARG_POS_CLASS, class_pair)
                l.append(tc)

            for complete_pair in completeness_list:
                for aln_method in aln_methods:
                    tc = SingleConfig(self, lang, ARG_POS_PROJ, complete_pair, aln_method)
                    l.append(tc)
        return l

    def projected(self, lang, align, completeness, condor=False):
        return self._f('{}_proj_{}_{}', self._tagged_dir(), lang, align, completeness, condor=condor)

    def classified(self, lang, cls, condor=False):
        return self._f('{}_class_{}', self._tagged_dir(), lang, cls, condor=condor)

    def tagger(self, lang, method, sub_method, name=False, prefix=False):
        basename = '{}_{}_{}'.format(lang, method, sub_method)
        prefix_path = os.path.join(self._tagger_dir(), basename)
        if name:
            return basename
        elif prefix:
            return prefix_path
        else:
            return prefix_path + '.tagger'

    def parser(self, lang, method, sub_method, name=False, prefix=False):
        basename = '{}'

    def tagger_name(self, lang, method, sub_method):
        return self.tagger(lang, method, sub_method, name=True)

    def rgigt(self, lang):
        return os.path.join(rg_igt_dir, '{}.xml'.format(lang))

    def xligt(self, lang):
        return os.path.join(xl_igt_dir, '{}.xml'.format(lang))

    def ud2(self, lang):
        two_letter_lang = lang_mapping.get(lang)
        if two_letter_lang is None:
            REPRO_LOG.critical('No two-letter language mapping found for language "{}"'.format(two_letter_lang))
        return os.path.join(os.path.join(ud2_dir, two_letter_lang), '{}-universal-test.conll'.format(two_letter_lang))

    def rgigt_eval(self, lang, method_string):
        return os.path.join(self._rgigt_eval_dir(), '{}_{}.txt'.format(lang, method_string))

    def xligt_eval(self, lang, method_string):
        return os.path.join(self._xligt_eval_dir(), '{}_{}.txt'.format(lang, method_string))



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

def enrich(ef: ExperimentFiles, overwrite = False, parse=True):
    """
    Enrich the files using all types of word alignment, and tag/parse the translation line.
    """

    enrichment_performed = False
    for lang in ef.langs:

        filtered_f = ef.filtered(lang)
        enriched_f = ef.enriched(lang)

        if not os.path.exists(enriched_f) or overwrite:

            # Notify user of enrichment if at least one file is being enriched.
            if not enrichment_performed:
                REPRO_LOG.log(NORM_LEVEL, "Enriching ODIN data.")

            if not USE_CONDOR:
                enrich_args = {ALN_VAR:aln_methods,
                               POS_VAR:[ARG_POS_TRANS],
                               ARG_INFILE:filtered_f,
                               ARG_OUTFILE:enriched_f}
                intent.commands.enrich.enrich()
            else:
                args = ['enrich',
                        '--align', ','.join(aln_methods),
                        '--pos', ARG_POS_TRANS,
                        filtered_f, enriched_f]
                if parse:
                    args += ['--parse', 'trans']

                condorify(args, ef._enriched_dir(condor=True), ef.enriched(lang, True))

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
    for tc in ef.tagger_configs():

        if not os.path.exists(tc.tagged()) or overwrite:

            if USE_CONDOR:
                args = tc.tag_args(True)
                condorify(*args)
            else:
                args = tc.tag_args(False)
                if tc.method == ARG_POS_CLASS:
                    intent.commands.enrich.enrich(**args)
                else:
                    do_projection(**args)

            tagging_performed = True

    if USE_CONDOR and (tagging_performed):
        if condor_email:
            condor.condor_wait_notify("Data has been tagged.", condor_email, "CONDOR: Tagging Complete")
        else:
            condor.condor_wait()


# -------------------------------------------
# Extract POS Taggers
# -------------------------------------------
def extract_pos(ef: ExperimentFiles, overwrite=False):
    extraction_performed = False
    for tc in ef.tagger_configs():
        if not os.path.exists(tc.tagger_path()) or overwrite:
            if USE_CONDOR:
                args = tc.extract_args(True)
                condorify(*args)
            else:
                args, kwargs = tc.extract_args(False)
                extract_from_xigt(args, **kwargs)

            extraction_performed = True

    if extraction_performed and USE_CONDOR:
        if condor_email:
            condor.condor_wait_notify("Taggers have been extracted.", condor_email, "CONDOR: POS Tagger Extraction Complete")
        else:
            condor.condor_wait()

# -------------------------------------------
# Eval POS Taggers on IGT
# -------------------------------------------
class TaggerEval(object):
    def __init__(self):
        self._matches = defaultdict(partial(defaultdict, int))
        self._compares = defaultdict(int)

    def add_tc(self, tc: SingleConfig, matches, compares):
        if tc.method == ARG_POS_CLASS:
            m_str = '{}_{}'.format(ARG_POS_CLASS, tc.c_name)
        else:
            m_str = '{}_{}_{}'.format(ARG_POS_PROJ, tc.aln_method, tc.complete_name)

        self._matches[tc.lang][m_str] = matches
        self._compares[tc.lang] = compares

    def langs(self):
        return sorted(self._compares.keys())

    def methods(self):
        m_s = set([])
        for lang in self._matches.keys():
            for m in self._matches[lang]:
                m_s.add(m)
        return sorted(m_s)

    def __str__(self, outstream = sys.stdout):
        ret_str = 'lang,' + ','.join(self.methods()) + '\n'
        for lang in self.langs():
            ret_str += '{},'.format(lang)
            ret_str += ','.join(['{:.1f}'.format(self._matches[lang][m]/self._compares[lang]*100) for m in self.methods()])
            ret_str += '\n'

        # Now, the overall...
        ret_str += 'overall'
        total_compares = sum(self._compares.values())
        for m in self.methods():
            total = 0
            for lang in self.langs():
                total += self._matches[lang][m]
            ret_str += ',{:.1f}'.format(total/total_compares*100)
        ret_str += '\n'

        return ret_str





def eval_taggers_igt(ef: ExperimentFiles, overwrite = False):
    evaluation_performed = False
    for tc in ef.tagger_configs():

        if not os.path.exists(tc.rgigt_eval()) or overwrite:

            if not evaluation_performed:
                REPRO_LOG.log(NORM_LEVEL, "Evaluating POS taggers on IGT data.")

            if USE_CONDOR:
                condorify(*tc.eval_igt_pos_args(True))
            else:
                args, kwargs = tc.eval_igt_pos_args(False)
                evaluate_intent(args, **kwargs)

            evaluation_performed = True

    if USE_CONDOR and evaluation_performed:
        if condor_email:
            condor.condor_wait_notify("IGT Evaluation Complete", condor_email, subject="IGT POS Evaluation Complete")
        else:
            condor.condor_wait()

    # -------------------------------------------
    # Now, consolidate all of the different methods and report.
    # -------------------------------------------
    te = TaggerEval()
    for tc in ef.tagger_configs():
        if not os.path.exists(tc.rgigt_eval()):
            REPRO_LOG.warn("Missing eval: {}".format(os.path.basename(tc.rgigt_eval())))
        else:
            with open(tc.rgigt_eval(), 'r') as f:
                data = f.readlines()
                filename, matches, compares, acc = data[-1].strip().split(',')
                te.add_tc(tc, int(matches), int(compares))

    print(te)


# =============================================================================

# =============================================================================
# Now to the main execution.
# =============================================================================

def reproduce(action):
    """
    :param action:
    """

    # =============================================================================
    # POS (IGT) Reproduction
    # =============================================================================
    if action == REPRO_POS_IGT:
        ef = ExperimentFiles(['spa', 'bul', 'fra', 'ita', 'deu'])
        filter(ef)
        enrich(ef)
        postag(ef, overwrite=False)
        extract_pos(ef, overwrite=False)
        eval_taggers_igt(ef)


    # =============================================================================
    # POS (Mono) Repro
    # =============================================================================
    elif action == REPRO_POS_MONO:
        ef = ExperimentFiles(['spa', 'swe', 'ind', 'deu', 'ita', 'por', 'fra'])
        filter(ef)
        enrich(ef)
        postag(ef, overwrite=False)

    # =============================================================================
    # DS Reproduction
    # =============================================================================
    elif action == REPRO_DS_IGT:
        ef = ExperimentFiles(['cym', 'deu', 'gle', 'hau', 'kor', 'plt', 'yaq'])
        filter(ef)
        enrich(ef)
        postag(ef, overwrite=False)
