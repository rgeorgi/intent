#!/usr/bin/env python3.4

import argparse
import sys
import logging


# Start the logger and set it up. ----------------------------------------------
from intent.scripts.basic.corpus_stats import igt_stats
from intent.scripts.basic.filter_corpus import filter_corpus
from intent.scripts.basic.split_corpus import split_corpus
from intent.scripts.evaluation import evaluate_intent
from intent.scripts.extraction import extract_from_xigt
from intent.utils.arg_consts import PARSE_LANG_PROJ, PARSE_TRANS, POS_TYPES, PARSE_TYPES, ALN_TYPES, ALN_VAR, POS_VAR, \
    PARSE_VAR
from intent.utils.listutils import flatten_list

logging.basicConfig(format=logging.BASIC_FORMAT)
MAIN_LOG = logging.getLogger('INTENT')

# ===============================================================================
# Check for dependencies...
# ===============================================================================

import_errors = False

try:
    import nltk
except ImportError:
    MAIN_LOG.critical('NLTK module not installed')
    import_errors = True

try:
    import lxml
except ImportError:
    MAIN_LOG.critical('lxml not installed.')
    import_errors = True

if import_errors:
    MAIN_LOG.critical('Necessary python modules were not found. Please install and try again.')
    sys.exit(2)


# ===============================================================================
# Set up the environment...
#===============================================================================

import intent.utils.env

from intent.utils.env import classifier

from intent.utils.argutils import DefaultHelpParser, existsfile, \
    PathArgException, csv_choices, proportion, globfiles

#===============================================================================
# Now, intialize the subcommands.
#===============================================================================



main = DefaultHelpParser(description="This is the main module for the INTENT package.",
                         formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                         fromfile_prefix_chars='@')

subparsers = main.add_subparsers(help='Valid subcommands', dest='subcommand')
subparsers.required = True

#===============================================================================
# Enrich subcommand
#===============================================================================
enrich = subparsers.add_parser('enrich', help='Enrich igt data.',
                               description='Ingest a XIGT document and add information, such as alignment, or POS tags.',
                               formatter_class=argparse.ArgumentDefaultsHelpFormatter)

enrich.add_argument('-v', '--verbose', action='count', help='Set the verbosity level.', default=0)

# Positional arguments ---------------------------------------------------------
enrich.add_argument('IN_FILE', type=existsfile, help='Input XIGT file.')
enrich.add_argument('OUT_FILE', help='Path to output XIGT file.')

# Optional arguments -----------------------------------------------------------
enrich.add_argument('--align', dest=ALN_VAR,
                    type=csv_choices(ALN_TYPES), default=[],
                    help='Comma-separated list of alignments to add. {}'.format(ALN_TYPES))

enrich.add_argument('--pos', dest=POS_VAR,
                    type=csv_choices(POS_TYPES), default=[],
                    help='''Comma-separated list of POS tags to add (no spaces):
                     {}'''.format(POS_TYPES))

enrich.add_argument('--parse', dest=PARSE_VAR,
                    type=csv_choices(PARSE_TYPES), default=[],
                    help='List of parses to create. {}'.format(PARSE_TYPES))

enrich.add_argument('--class', dest='class_path', default=classifier)

#===============================================================================
# ODIN subcommand
#===============================================================================
odin = subparsers.add_parser('odin', help='Convert ODIN data to XIGT format')

odin.add_argument('-v', '--verbose', action='count', help='Set the verbosity level.', default=0)
odin.add_argument('--format', help='Format to output odin data in.', choices=['txt', 'xigt'], default='xigt')
odin.add_argument('LNG', help='ISO 639-3 code for a language')
odin.add_argument('OUT_FILE', help='Output path for the output file.')
odin.add_argument('--limit', help="Limit number of instances written.", type=int)
odin.add_argument('--randomize', action='store_true', help='Randomly select the instances')

#===============================================================================
# STATS subcommand
#
# Get statistics (# sents, # tokens, tags/token, etc) for a XIGT file.
#===============================================================================
stats = subparsers.add_parser('stats', help='Get corpus statistics for a set of XIGT files.')

stats.add_argument('FILE', nargs='+', help='Files from which to gather statistics.')
stats.add_argument('-v', '--verbose', action='count', help='Set the verbosity level.', default=0)

#===============================================================================
# SPLIT subcommand
#
# Split XIGT file into train/dev/test
#===============================================================================
split = subparsers.add_parser('split', help='Command to split input file(s) into train/dev/test instances.')

split.add_argument('FILE', nargs='+', help='XIGT files to gather together in order to generate the train/dev/test split', type=globfiles)
split.add_argument('--train', default=0.8, help='The proportion of the data to set aside for training.', type=proportion)
split.add_argument('--dev', default=0.1, help='The proportion of data to set aside for development.', type=proportion)
split.add_argument('--test', default=0.1, help='The proportion of data to set aside for testing.', type=proportion)
split.add_argument('-v', '--verbose', action='count', help='Set the verbosity level.', default=0)
split.add_argument('-o', dest='prefix', default=None, help='Destination prefix for the output.', required=True)
split.add_argument('-f', dest='overwrite', action='store_true', help='Force overwrite of existing files.')

#===============================================================================
# FILTER subcommand
#
# Filter XIGT files for L,G,T lines, 1-to-1 alignment, etc.
#===============================================================================

filter_p = subparsers.add_parser('filter', help='Command to filter input file(s) for instances')

filter_p.add_argument('FILE', nargs='+', help='XIGT files to filter.', type=globfiles)
filter_p.add_argument('-o', '--output', help='Output file (Combine from inputs)', required=True)
filter_p.add_argument('--require-lang', help='Require instances to have language line', choices=['true','false'], default='true')
filter_p.add_argument('--require-gloss', help='Require instances to have gloss line', choices=['true', 'false'], default='true')
filter_p.add_argument('--require-trans', help='Require instances to have trans line', choices=['true', 'false'], default='true')

filter_p.add_argument('--require-gloss-pos', help='Require instance to have gloss pos tags', choices=['true', 'false'], default='false')

filter_p.add_argument('--require-aln', help='Require instances to have 1-to-1 gloss/lang alignment.', choices=['true','false'], default='true')
filter_p.add_argument('-v', '--verbose', action='count', help='Set the verbosity level.', default=0)

#===============================================================================
# EXTRACT subcommand
#
# Extract useful things from a series of enriched XIGT-XML files, such as
# a POS classifier for the gloss line, or CFG rules from projected trees, etc.
#===============================================================================

extract_p = subparsers.add_parser('extract', help='Command to extract data from enriched XIGT-XML files')

extract_p.add_argument('FILE', nargs='+', help='XIGT files to include.', type=globfiles)
extract_p.add_argument('--gloss-classifier', help='Output prefix for gloss-line classifier (No extension).')
extract_p.add_argument('--cfg-rules', help='Output path for cfg-rules.')
extract_p.add_argument('-v', '--verbose', action='count', help='Set the verbosity level.', default=0)

#===============================================================================
# EVAL subcommand
#
# Used for evaluating different portions of INTENT's functions against a gold-standard
# XIGT-XML file.
#===============================================================================

eval_p = subparsers.add_parser('eval', help='Command to eval INTENT functions against a gold-standard XIGT-XML.')

eval_p.add_argument('FILE', nargs='+', help='XIGT files to test against.', type=globfiles)
eval_p.add_argument('--classifier', help='Specify a gloss-line POS classifier to test.')
eval_p.add_argument('--alignment', help='Test alignment methods against the alignment provided in the file.')

eval_p.add_argument('-v', '--verbose', action='count', help='Set the verbosity level.', default=0)

# Parse the args. --------------------------------------------------------------
try:
    args = main.parse_args()
except PathArgException as pae:  # If we get some kind of invalid file in the arguments, print it and exit.
    MAIN_LOG.critical(str(pae))
    # sys.stderr.write(str(pae)+'\n')
    sys.exit(2)


# Decide on action based on subcommand and args. -------------------------------
from intent import subcommands

#===============================================================================
# Set verbosity level
#===============================================================================

logging.getLogger().setLevel(logging.WARNING - 10 * (min(args.verbose, 2)))

if args.subcommand == 'enrich':
    subcommands.enrich(**vars(args))
elif args.subcommand == 'odin':
    subcommands.odin(**vars(args))
elif args.subcommand == 'stats':
    igt_stats(flatten_list(args.FILE), type='xigt')
elif args.subcommand == 'split':
    split_corpus(flatten_list(args.FILE), args.train, args.dev, args.test, prefix=args.prefix, overwrite=args.overwrite)
elif args.subcommand == 'filter':
    filter_corpus(flatten_list(args.FILE), args.output, args.require_lang, args.require_gloss, args.require_trans, args.require_aln, args.require_gloss_pos)
elif args.subcommand == 'extract':
    extract_from_xigt(flatten_list(args.FILE), args.gloss_classifier, args.cfg_rules)
elif args.subcommand == 'eval':
    evaluate_intent(flatten_list(args.FILE), args.classifier, args.alignment)