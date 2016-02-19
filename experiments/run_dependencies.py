#!/usr/bin/env python3
import os, sys, logging

from subprocess import Popen



"""
This module is used to:

1) Retrieve the xigt-formatted language data
   from ODIN

2a) Parse the translation lines
2b) POS tag (via classification) the gloss lines
2c) Align translation and gloss lines with the
    various methods, heuristic and giza

3) For each alignment method, create a new set of
   files for each language that have POS tags and
   dependency structures projected using that alignment
   method.

4) Train dependency parsers based on each set of projected
   trees from #3, using both classifier-produced
   POS tags as well as the projection-produced POS tags.

5) Evaluate against the universal dependency treebank, making
   sure to strip the gold-standard POS tags and features from
   the data, replacing the POS tags with those produced by the
   tagger trained with the POS tags obtained with each method
   in #4.
"""

# -------------------------------------------
# Change these to reflect where each set of docs
# are kept.
# -------------------------------------------

# Whether or not to use the condor-submit capability
# for paralellization
from collections import defaultdict


# Use condor, and email when tasks finish.
USE_CONDOR = False
email_address = 'rgeorgi@uw.edu'

this_dir = os.path.dirname(__file__)

# The directory where the universal dependency treebanks are stored.
eval_dir = '/Users/rgeorgi/Documents/treebanks/universal_treebanks_v2.0/std'

# -------------------------------------------
# Here is a map to go from the three-letter codes
# used in ODIN to the two letter codes used in the
# universal dependency treebank.
# -------------------------------------------
lang_map = {'deu':'ger',
            'gla':'gli',
            'hau':'hua',
            'kor':'kkn',
            'cym':'wls',
            'yaq':'yaq'}

eval_suffix = '_dep_train.txt'

# The directory in which the files will be created for this experiment.
experiment_dir = os.path.join(this_dir, 'dependencies')

# The directory where the ODIN by-lang XIGT files are found.
odin_lang_dir = os.path.join(this_dir, 'odin-data')





# -------------------------------------------
logging.basicConfig(level=logging.INFO)
enrich_dir = os.path.join(experiment_dir, 'enriched')
# Directory where INTENT is located...
intent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
intent_script = os.path.join(intent_dir, 'intent.py')
sys.path.insert(0, intent_dir)

os.environ["PATH"]=os.getenv("PATH")+':'.join(sys.path)

from intent.utils import env
from intent.commands.extraction import extract_from_xigt
from intent.commands.project import do_projection
from intent.interfaces.condor import run_cmd, condor_wait, condor_wait_notify
from intent.scripts.eval.dep_parser import eval_mst
from intent.commands.enrich import enrich
from intent.commands.filter import filter_corpus
from intent.corpora.conll import eval_conll_paths
from intent.consts import *


pos_methods = [ARG_POS_PROJ, ARG_POS_CLASS]
aln_methods = ARG_ALN_METHODS

filenames = {l:l+'.xml' for l in lang_map.keys()}

# -------------------------------------------
# 0) Start by building up a list of all the
#    directories we wish to create
# -------------------------------------------


class ExperimentFiles(object):
    def __init__(self, langs):
        self.langs = langs

    def get_original_file(self, lang):
        return os.path.join(odin_lang_dir, '{}.xml'.format(lang))

    def _enriched_dir(self):
        return os.path.join(experiment_dir, 'enriched')

    def _filtered_dir(self):
        return os.path.join(experiment_dir, 'filtered')

    def _project_dir(self):
        return os.path.join(experiment_dir, 'projected')

    def _parser_dir(self):
        return os.path.join(experiment_dir, 'parsers')

    def _results_dir(self):
        return os.path.join(experiment_dir, 'results')

    def get_enriched_file(self, lang):
        return os.path.join(os.path.join(self._enriched_dir(), '{}_enriched.xml'.format(lang)))

    def get_filtered_file(self, lang):
        return os.path.join(os.path.join(self._filtered_dir(), '{}_filtered.xml'.format(lang)))

    def get_projected_file(self, aln_method, lang):
        proj_dir = os.path.join(experiment_dir, 'projected')
        filename = '{}_{}_projected.xml'.format(lang, aln_method)
        return os.path.join(proj_dir, filename)


    def _config_name(self, aln_method, pos_source, lang):
        if aln_method is None:
            filename = '{}_{}'.format(lang, pos_source)
        else:
            filename = '{}_{}_{}'.format(lang, aln_method, pos_source)
        return filename

    def get_model_prefix(self, aln_method, pos_source, lang):
        return os.path.join(self._parser_dir(), self._config_name(aln_method, pos_source, lang))

    def get_tagger(self, aln_method, pos_source, lang):
        return self.get_model_prefix(aln_method, pos_source, lang) + '.tagger'

    def get_parser(self, aln_method, pos_source, lang):
        return self.get_model_prefix(aln_method, pos_source, lang) + '.depparser'

    def get_condor_filter(self, lang):
        return os.path.join(self._filtered_dir(), 'condor'), '{}_filtered'.format(lang)

    def get_condor_enrich(self, lang):
        return os.path.join(self._enriched_dir(), 'condor'), '{}_enrich'.format(lang)

    def get_condor_project(self, aln_method, lang):
        return os.path.join(self._project_dir(), 'condor'), '{}_{}_project'.format(lang, aln_method)

    def get_condor_extract(self, aln_method, pos_source, lang):
        return os.path.join(self._parser_dir(), 'condor'), self._config_name(aln_method, pos_source, lang)

    def get_condor_result(self, aln_method, pos_source, lang):
        return os.path.join(self._results_dir(), 'condor'), self._config_name(aln_method, pos_source, lang)

    def parser_configs(self):
        configs = []
        for lang in self.langs:
            configs.append((None, ARG_POS_CLASS, lang, self.get_enriched_file(lang)))
            for aln_method in aln_methods:
                configs.append((aln_method, ARG_POS_PROJ, lang, self.get_projected_file(aln_method, lang)))
        return configs

    def filtered_done(self):
        all_present = True
        for lang in self.langs:
            if not os.path.exists(self.get_filtered_file(lang)):
                all_present = False
                break
        return all_present

    # -------------------------------------------
    # The conll eval files
    # -------------------------------------------
    def get_eval_file(self, lang):
        mapped_lang = lang_map[lang]
        eval_path = os.path.join(os.path.join(eval_dir, mapped_lang), '{}{}'.format(mapped_lang, eval_suffix))
        return eval_path

    def get_out_prefix(self, lang, aln_method, pos_source):
        return os.path.join(self._results_dir(), self._config_name(aln_method, pos_source, lang))




ef = ExperimentFiles(lang_map.keys())

# -------------------------------------------
# 1) Filter the data
# -------------------------------------------
filtration_done = False
for lang in ef.langs:
    orig_f = ef.get_original_file(lang)
    filtered_f = ef.get_filtered_file(lang)

    if not os.path.exists(filtered_f):
        filtration_done = True
        if USE_CONDOR:
            model_prefix, name = ef.get_condor_filter(lang)
            run_cmd(['intent.py', 'filter', '--require-aln', '--require-gloss', '--require-trans', '--require-lang', orig_f, filtered_f], model_prefix, name, False)
        else:
            filter_corpus([orig_f], filtered_f, require_lang=True, require_gloss=True, require_trans=True, require_aln=True)

if USE_CONDOR and filtration_done:
    condor_wait_notify("Data has been filtered.", email_address, "CONDOR: Filtration complete.")


# -------------------------------------------
# 2) Enriched data
# -------------------------------------------
enrichment_done = False
for lang in ef.langs:
    filtered_f = ef.get_filtered_file(lang)
    enriched_f = ef.get_enriched_file(lang)

    if not os.path.exists(enriched_f):
        enrichment_done = True
        if USE_CONDOR:
            model_prefix, name = ef.get_condor_enrich(lang)
            run_cmd(['intent.py', 'enrich', '--align', 'heur,heurpos,giza,gizaheur', '--pos class', '--parse trans', filtered_f, enriched_f],
                    model_prefix, name, False)
        else:
            enrich(**{ARG_INFILE:filtered_f, ARG_OUTFILE:enriched_f, ALN_VAR:ARG_ALN_METHODS, POS_VAR:ARG_POS_CLASS, PARSE_VAR:ARG_PARSE_TRANS})

if USE_CONDOR and enrichment_done:
    condor_wait_notify("Data has been enriched.", email_address, "CONDOR: Enrichment Complete.")

# -------------------------------------------
# 3) Re-project the data...
# -------------------------------------------
projection_done = False
for lang in ef.langs:
    for aln_method in aln_methods:
        enriched_f  = ef.get_enriched_file(lang)
        projected_f = ef.get_projected_file(aln_method, lang)

        if not os.path.exists(projected_f):
            projection_done = True
            if USE_CONDOR:
                model_prefix, name = ef.get_condor_project(aln_method, lang)
                run_cmd(['intent.py', 'project', '--aln-method', aln_method, '--completeness', '1.0',
                         enriched_f, projected_f], model_prefix, name, False)

            else:
                # p = Popen(['intent.py', 'project', '--aln-method', aln_method, enriched_f, projected_f, '-v'], env={"PATH":os.getenv("PATH")+':/Users/rgeorgi/Documents/code/intent'})
                # p.wait()
                do_projection(**{ARG_INFILE:enriched_f, 'aln_method':aln_method, ARG_OUTFILE:projected_f, 'completeness':1.0})

if USE_CONDOR and projection_done:
    condor_wait_notify("Data has been projected.", email_address, "CONDOR: Projection Complete.")

# -------------------------------------------
# 4) Now, extract the parsers.
# -------------------------------------------
extraction_done = False
for lang in ef.langs:
    for aln_method in aln_methods:
        for pos_source in pos_methods:
            model_prefix = ef.get_model_prefix(aln_method, pos_source, lang)

            tagger_path = ef.get_tagger(aln_method, pos_source, lang)
            parser_path = ef.get_tagger(aln_method, pos_source, lang)

            projected_f = ef.get_projected_file(aln_method, lang)


            if not os.path.exists(tagger_path) or not os.path.exists(parser_path):
                extraction_done = True

                # -------------------------------------------
                # Set up the arguments for making the external call
                # -------------------------------------------
                args = ['intent.py', 'extract',
                        '--tagger-prefix', model_prefix,
                        '--use-align', aln_method,
                        '--dep-prefix', model_prefix,
                        '--use-pos', pos_source, projected_f]

                # -------------------------------------------
                # CONDOR
                # -------------------------------------------
                if USE_CONDOR:
                    prefix, name = ef.get_condor_extract(aln_method, pos_source, lang)
                    run_cmd(args, prefix, name, False)
                else:
                    # extract_from_xigt([source_file], tagger_prefix=model_prefix,
                    #                   dep_prefix=model_prefix, pos_method=ARG_POS_PROJ,
                    #                   aln_method=aln_method)
                    p = Popen(args+['-v'])
                    p.wait()

if USE_CONDOR and extraction_done:
    condor_wait_notify("Parsers have been extracted.", email_address, "CONDOR: Extraction complete.")

# -------------------------------------------
# 5) Finally, evaluate all the parsers.
# -------------------------------------------
class DepEvals():
    def __init__(self):
        self.statdict = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        self.overall = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    def add(self, lang, aln_method, pos_source, val, matches, compares):
        self.statdict[lang][aln_method][pos_source] = val
        self.overall[aln_method][pos_source]['matches'] += matches
        self.overall[aln_method][pos_source]['compares'] += compares

    def overall_acc(self, am, pos_source):
        return self.overall[am][pos_source]['matches'] / self.overall[am][pos_source]['compares'] * 100

    def print_stats(self, pos_source):
        print(','.join(['lang']+[a for a in sorted(aln_methods)]))
        for lang in sorted(self.statdict.keys()):
            print(lang, end=',')
            accs = [self.statdict[lang][aln_method][pos_source] for aln_method in sorted(aln_methods)]
            accs = ['{:.2f}'.format(a) for a in accs]
            print(','.join(accs))
        print('overall',end=',')
        overallaccs = ['{:.2f}'.format(self.overall_acc(am, pos_source)) for am in sorted(aln_methods)]
        print(','.join(overallaccs))



de_short = DepEvals()
de_long  = DepEvals()

for lang in ef.langs:
    for aln_method in aln_methods:
        for pos_source in pos_methods:
            model_prefix = ef.get_model_prefix(aln_method, pos_source, lang)

            tagger_path = ef.get_tagger(aln_method, pos_source, lang)
            parser_path = ef.get_parser(aln_method, pos_source, lang)

            eval_path   = ef.get_eval_file(lang)
            out_prefix  = ef.get_out_prefix(lang, aln_method, pos_source)

            if not os.path.exists(eval_path) or not os.path.exists(out_prefix):

                if USE_CONDOR:
                    prefix, name = ef.get_condor_result(aln_method, pos_source, lang)
                    eval_script = os.path.join(intent_dir, 'intent/scripts/eval/dep_parser.py')
                    run_cmd([eval_script, 'test', '-p', parser_path, '-t', tagger_path, '--test', eval_path,
                             '-o', out_prefix], prefix, name, False, env='PYTHONPATH={}'.format(intent_dir))
                else:
                    # eval_mst(parser_path, eval_path, out_prefix, tagger=tagger_path)
                    ce = eval_conll_paths(eval_path, out_prefix+'_out_tagged.txt')
                    de_short.add(lang, aln_method, pos_source, ce.short_ul(), ce.short_ul_count(), ce.short_words())
                    de_long.add(lang, aln_method, pos_source, ce.long_ul(), ce.long_ul_count(), ce.long_words())


de_short.print_stats(ARG_POS_PROJ)
de_long.print_stats(ARG_POS_PROJ)

de_short.print_stats(ARG_POS_CLASS)
de_long.print_stats(ARG_POS_CLASS)

if USE_CONDOR:
    condor_wait_notify("Evaluation completed.", email_address, "CONDOR: Evaluation complete.")
