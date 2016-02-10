#!/usr/bin/env python3
import os, sys, logging
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

from intent.utils import env
from intent.commands.extraction import extract_from_xigt
from intent.commands.project import do_projection
from intent.interfaces.condor import run_cmd, condor_wait, condor_wait_notify
from intent.scripts.eval.dep_parser import eval_mst
from intent.commands.enrich import enrich
from intent.commands.filter import filter_corpus
from intent.consts import *

# -------------------------------------------
# Here is a map to go from the three-letter codes
# used in ODIN to the two letter codes used in the
# universal dependency treebank.
# -------------------------------------------
lang_map = {'deu':'de',
            'fra':'fr',
            'ind':'id',
            'spa':'es',
            'ita':'it',
            'swe':'sv'}

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

    def get_enriched_file(self, lang):
        return os.path.join(os.path.join(self._enriched_dir(), '{}_enriched.xml'.format(lang)))

    def get_filtered_file(self, lang):
        return os.path.join(os.path.join(self._filtered_dir(), '{}_filtered.xml'.format(lang)))

    def get_projected_file(self, aln_method, lang):
        proj_dir = os.path.join(experiment_dir, 'projected')
        filename = '{}_{}_projected.xml'.format(lang, aln_method)
        return os.path.join(proj_dir, filename)

    def get_parser(self, aln_method, pos_source, lang):
        return os.path.join(self._parser_dir(), '{}_{}_{}'.format(lang, aln_method, pos_source))

    def get_tagger(self, aln_method, pos_source, lang):
        if aln_method is None:
            filename = '{}_{}'.format(lang, pos_source)
        else:
            filename = '{}_{}_{}'.format(lang, aln_method, pos_source)

        return os.path.join(self._parser_dir(), filename)


    def get_condor_filter(self, lang):
        return os.path.join(self._filtered_dir(), 'condor'), '{}_filtered'.format(lang)

    def get_condor_enrich(self, lang):
        return os.path.join(self._enriched_dir(), 'condor'), '{}_enrich'.format(lang)

    def get_condor_project(self, aln_method, lang):
        return os.path.join(self._project_dir(), 'condor'), '{}_{}_project'.format(lang, aln_method)

    def get_condor_extract(self, aln_method, pos_source, lang):
        if aln_method is not None:
            name = '{}_{}_{}'.format(lang, aln_method, pos_source)
        else:
            name = '{}_{}'.format(lang, pos_source)
        return os.path.join(self._parser_dir(), 'condor'), name


    def filtered_done(self):
        all_present = True
        for lang in self.langs:
            if not os.path.exists(self.get_filtered_file(lang)):
                all_present = False
                break
        return all_present


ef = ExperimentFiles(lang_map.keys())

# -------------------------------------------
# 1) Filter the data
# -------------------------------------------
for lang in ef.langs:
    orig_f = ef.get_original_file(lang)
    filtered_f = ef.get_filtered_file(lang)

    if USE_CONDOR:
        prefix, name = ef.get_condor_filter(lang)
        run_cmd(['intent.py', 'filter', '--require-aln', '--require-gloss', '--require-trans', '--require-lang', orig_f, filtered_f], prefix, name, False)
    else:
        filter_corpus([orig_f], filtered_f, require_lang=True, require_gloss=True, require_trans=True, require_aln=True)

if USE_CONDOR:
    condor_wait_notify("Data has been filtered.", email_address, "CONDOR: Filtration complete.")


# -------------------------------------------
# 2) Enriched data
# -------------------------------------------
for lang in ef.langs:
    filtered_f = ef.get_original_file(lang)
    enriched_f = ef.get_enriched_file(lang)

    if USE_CONDOR:
        prefix, name = ef.get_condor_enrich(lang)
        run_cmd(['intent.py', 'enrich', '--align', 'heur,heurpos,giza,gizaheur', '--pos class', '--parse trans', filtered_f, enriched_f],
                prefix, name, False)
    else:
        enrich(**{ARG_INFILE:filtered_f, ARG_OUTFILE:enriched_f, ALN_VAR:ARG_ALN_METHODS, POS_VAR:ARG_POS_CLASS, PARSE_VAR:ARG_PARSE_TRANS})

if USE_CONDOR:
    condor_wait_notify("Data has been enriched.", email_address, "CONDOR: Enrichment Complete.")

# -------------------------------------------
# 3) Re-project the data...
# -------------------------------------------
for lang in ef.langs:
    for aln_method in aln_methods:
        enriched_f  = ef.get_enriched_file(lang)
        projected_f = ef.get_projected_file(aln_method, lang)

        if USE_CONDOR:
            prefix, name = ef.get_condor_project(aln_method, lang)
            run_cmd(['intent.py', 'project', '--aln-method', aln_method, enriched_f, projected_f], prefix, name, False)

        else:
            do_projection(**{ARG_INFILE:enriched_f, aln_method:aln_method, ARG_OUTFILE:projected_f})

# -------------------------------------------
# Wait for the condor tasks to complete, and
# send an email at this point.
# -------------------------------------------
if USE_CONDOR:
    condor_wait_notify("Data has been projected.", email_address, "CONDOR: Projection Complete.")

# -------------------------------------------
# 4) Now, extract the parsers.
# -------------------------------------------
parse_tag_pairs = []

for lang in ef.langs:

    # -------------------------------------------
    # Get the classifier-based taggers.
    # -------------------------------------------
    enriched_f = ef.get_enriched_file(lang)
    class_tagger_prefix = ef.get_tagger(None, ARG_POS_CLASS, lang)
    if USE_CONDOR:
        prefix, name = ef.get_condor_extract(None, ARG_POS_CLASS, lang)
        run_cmd(['intent.py', 'extract', '--tagger-prefix', class_tagger_prefix, '--use-pos', ARG_POS_CLASS, enriched_f], prefix, name, False)
    else:
        extract_from_xigt([enriched_f], tagger_prefix=class_tagger_prefix, pos_method=ARG_POS_CLASS)

    # -------------------------------------------
    # Now, the projection based taggers and parsers.
    # -------------------------------------------
    for aln_method in aln_methods:
        projected_f        = ef.get_projected_file(aln_method, lang)
        proj_tagger_prefix = ef.get_tagger(aln_method, ARG_POS_PROJ, lang)
        dep_parser_prefix  = ef.get_parser(aln_method, ARG_POS_PROJ, lang)

        if USE_CONDOR:
            prefix, name = ef.get_condor_extract(aln_method, ARG_POS_PROJ, lang)
            run_cmd(['intent.py', 'extract', '--tagger-prefix', proj_tagger_prefix, '--dep-prefix', dep_parser_prefix,
                     '--use-pos', ARG_POS_PROJ, projected_f], prefix, name, False)
        else:
            extract_from_xigt([projected_f], tagger_prefix=proj_tagger_prefix,
                              dep_prefix=dep_parser_prefix, pos_method=ARG_POS_PROJ, aln_method=aln_method)

if USE_CONDOR:
    condor_wait_notify("Parsers have been extracted.", email_address, "CONDOR: Extraction complete.")

sys.exit()
# -------------------------------------------
# 5) Finally, evaluate all the parsers.
# -------------------------------------------
for lang, parser, tagger in parse_tag_pairs:

    parser_dir = os.path.dirname(parser)

    two_letter_lang = lang_map[lang]
    eval_path = os.path.join(os.path.join(eval_dir, two_letter_lang), '{}-universal-test.conll'.format(two_letter_lang))
    out_prefix = os.path.splitext(parser)[0]



    if USE_CONDOR:
        eval_script = os.path.join(intent_dir, 'intent/scripts/eval/dep_parser.py')
        run_cmd([eval_script, 'test', '-p', parser, '-t', tagger, '--test', eval_path,
                 '-o', out_prefix],
                os.path.join(parser_dir, 'condor'),
                'eval_'+os.path.basename(os.path.splitext(parser)[0]),
                False, env='PYTHONPATH={}'.format(intent_dir))
    else:
        eval_mst(parser, eval_path, out_prefix, tagger=tagger)