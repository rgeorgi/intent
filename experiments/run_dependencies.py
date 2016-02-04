#!/usr/bin/env python3
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

USE_CONDOR = False

# The directory where the universal dependency treebanks are stored.
eval_dir = '/Users/rgeorgi/Documents/treebanks/universal_treebanks_v2.0/std'

# The directory where the ODIN by-lang XIGT files are found.
odin_lang_dir = '/Users/rgeorgi/Documents/code/intent/experiments/dependencies/original'

# The directory in which the files will be created for this experiment.
experiment_dir = '/Users/rgeorgi/Documents/code/intent/experiments/dependencies/'

# -------------------------------------------
import os, sys, logging
logging.basicConfig(level=logging.INFO)
enrich_dir = os.path.join(experiment_dir, 'enriched')
# Directory where INTENT is located...
intent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
intent_script = os.path.join(intent_dir, 'intent.py')
sys.path.insert(0, intent_dir)

from intent.utils import env
from intent.commands.extraction import extract_from_xigt
from intent.commands.project import do_projection
from intent.interfaces.condor import run_cmd, condor_wait
from intent.scripts.eval.dep_parser import eval_mst
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

pos_methods = ['proj', 'class']
aln_methods = ARG_ALN_METHODS

filenames = {l:l+'.xml' for l in lang_map.keys()}

# -------------------------------------------
# 2) Enriched data
# -------------------------------------------
enriched_files = [os.path.join(enrich_dir, fn) for fn in sorted(filenames.values())]

# -------------------------------------------
# 3)
# -------------------------------------------
proj_method_dirs = {m:os.path.join(experiment_dir+'proj-{}'.format(m)) for m in aln_methods}

for aln_method in proj_method_dirs.keys():
    method_dir = proj_method_dirs[aln_method]
    print('--- 3) Now re-projecting using alignment method "{}" in directory "{}"'.format(aln_method, method_dir))

    for enriched_file in enriched_files:
        print('Reprojecting file "{}"'.format(os.path.basename(enriched_file)))
        projected_file = os.path.join(method_dir, os.path.basename(enriched_file))
        if not os.path.exists(projected_file):
            if USE_CONDOR:
                run_cmd(['intent.py', 'project', '--aln-method', aln_method, enriched_file, projected_file],
                        os.path.join(method_dir, 'condor'),
                        os.path.splitext(os.path.basename(enriched_file))[0],
                        False)
            else:
                do_projection(**{ARG_INFILE:enriched_file, aln_method:aln_method, ARG_OUTFILE:projected_file})


# -------------------------------------------
# Wait for the condor tasks to complete, and
# send an email at this point.
# -------------------------------------------
if USE_CONDOR:
    condor_wait()
    os.system('echo "{}" | mail -s "{}" {}'.format("All projection processes have finished.",
                                                   "Condor Notification",
                                                   "rgeorgi@uw.edu"))

# -------------------------------------------
# 4) Now, extract the parsers.
# -------------------------------------------
parse_tag_pairs = []

for aln_method in proj_method_dirs.keys():
    proj_dir = proj_method_dirs[aln_method]
    for basename in sorted(filenames.values()):

        lang = os.path.splitext(basename)[0]

        # Get the projected file to extract from...
        proj_file = os.path.join(proj_dir, basename)
        # Now, extract using both classifier and projection methods
        for pos_source in pos_methods:

            prefix = os.path.join(proj_dir, os.path.splitext(os.path.basename(proj_file))[0] + '_' + pos_source)
            parser = prefix+'.depparser'
            tagger = prefix+'.tagger'
            parse_tag_pairs.append((lang, parser, tagger))

            print(parser, tagger)
            # if not os.path.exists(parser) or not os.path.exists(tagger):
            if False:
                if USE_CONDOR:
                    run_cmd(['intent.py', 'extract', '--tagger-prefix', prefix, '--dep-prefix', prefix,
                             '--use-pos', pos_source],
                            os.path.join(proj_dir, 'condor'),
                            'extract_'+os.path.splitext(basename)[0],
                            False)
                else:
                    extract_from_xigt([proj_file], tagger_prefix=prefix,
                                      dep_prefix=prefix, pos_method=pos_source, aln_method=aln_method)

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