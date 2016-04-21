#!/usr/bin/env python3

import argparse
import logging
import sys

# -------------------------------------------
# Start the logger.
# -------------------------------------------
logging.basicConfig(format=logging.BASIC_FORMAT)
MAIN_LOG = logging.getLogger('INTENT')

# -------------------------------------------
# Check for dependencies.
# -------------------------------------------

import_errors = False

try:
    import nltk
except ImportError:
    MAIN_LOG.critical('NLTK module not installed')
    import_errors = True

if import_errors:
    MAIN_LOG.critical('Necessary python modules were not found. Please install and try again.')
    sys.exit(2)

# =============================================================================
# Commands
# =============================================================================
CMD_PROJECT = 'project'
CMD_EVAL    = 'eval'
CMD_FILTER  = 'filter'
CMD_STATS   = 'stats'
CMD_ENRICH  = 'enrich'
CMD_SPLIT   = 'split'
CMD_EXTRACT = 'extract'
CMD_TEXT    = 'text'
# =============================================================================


# -------------------------------------------
# Import the env module, since there are some
# additional tests there.
# -------------------------------------------
from intent.utils import env

# -------------------------------------------
# Start the logger and set it up.
# -------------------------------------------
from intent.commands.corpus_stats import igt_stats
from intent.commands.filter import filter_corpus
from intent.commands.split_corpus import split_corpus
from intent.commands.text_to_xigt import text_to_xigtxml
from intent.commands.evaluation import evaluate_intent
from intent.commands.extraction import extract_from_xigt
from intent.commands.enrich import enrich
from intent.commands.project import do_projection
from intent.consts import *
from intent.utils.listutils import flatten_list
from xigt.codecs.xigtxml import dump
from intent.utils.env import classifier
from intent.utils.argutils import DefaultHelpParser, existsfile, \
    PathArgException, csv_choices, proportion, globfiles, writefile

#===============================================================================
# Now, intialize the subcommands.
#===============================================================================



main = DefaultHelpParser(description="This is the main module for the INTENT package.",
                         formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                         fromfile_prefix_chars='@')

subparsers = main.add_subparsers(help='Valid subcommands', dest='subcommand')
subparsers.required = True

def add_verbose(p):
    p.add_argument('-v', '--verbose', action='count', help='Set the verbosity level.', default=0)


def register_subparser(name, help=None, description=None, **kwargs) -> argparse.ArgumentParser:
    """
    Use this function to create regularized subparser.

    :param name: The name of the parser.
    :param help:
    :param description:
    :param kwargs: Any other arguments
    :return: The subparser
    """
    p = subparsers.add_parser(name, help=help, description=description, **kwargs)
    add_verbose(p)
    return p

#===============================================================================
# Enrich subcommand
#===============================================================================
enrich_p = register_subparser(CMD_ENRICH, help='Enrich igt data.',
                                 description='Ingest a XIGT document and add information, such as alignment, or POS tags.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

# Positional arguments ---------------------------------------------------------
enrich_p.add_argument(ARG_INFILE, type=existsfile, help='Input XIGT file.')
enrich_p.add_argument(ARG_OUTFILE, help='Path to output XIGT file.')

# Optional arguments -----------------------------------------------------------
enrich_p.add_argument('--align', dest=ALN_VAR,
                      type=csv_choices(ARG_ALN_METHODS), default=[],
                      help='Comma-separated list of alignments to add. {}'.format(ARG_ALN_METHODS))

enrich_p.add_argument('--giza-symmetric', dest=ALN_SYM_VAR, choices=ALN_SYM_TYPES,
                      help='Symmetricization heuristic to apply to statistical alignment',
                      default=None)

enrich_p.add_argument('--pos', dest=POS_VAR,
                      type=csv_choices(ARG_POS_ENRICH_METHODS), default=[],
                      help='''Comma-separated list of POS tags to add (no spaces):
                     {}'''.format(ARG_POS_ENRICH_METHODS))

enrich_p.add_argument('--parse', dest=PARSE_VAR,
                      type=csv_choices(PARSE_TYPES), default=[],
                      help='List of parses to create. {}'.format(PARSE_TYPES))

enrich_p.add_argument('--max-parse-length', dest='max_parse_length', default=25,
                      help='What is the maximum length to attempt parsing on?', type=int)

enrich_p.add_argument('--class', dest='class_path', default=classifier)

enrich_p.add_argument('--proj-aln', dest='proj_aln', choices=ARG_ALN_METHODS_ALL, default=ARG_ALN_ANY,
                      help='Alignment to use when performing projection. Can use "any" for any available alignment.')

#===============================================================================
# STATS subcommand
#
# Get statistics (# sents, # tokens, tags/token, etc) for a XIGT file.
#===============================================================================
stats_p = register_subparser(CMD_STATS, help='Get corpus statistics for a set of XIGT files.')
stats_p.add_argument('FILE', nargs='+', help='Files from which to gather statistics.', type=globfiles)


#===============================================================================
# SPLIT subcommand
#
# Split XIGT file into train/dev/test
#===============================================================================
split_p = register_subparser(CMD_SPLIT, help='Command to split input file(s) into train/dev/test instances.')

split_p.add_argument('FILE', nargs='+', help='XIGT files to gather together in order to generate the train/dev/test split', type=globfiles)
split_p.add_argument('--train', default=0.8, help='The proportion of the data to set aside for training.', type=proportion)
split_p.add_argument('--dev', default=0.1, help='The proportion of data to set aside for development.', type=proportion)
split_p.add_argument('--test', default=0.1, help='The proportion of data to set aside for testing.', type=proportion)
split_p.add_argument('-o', dest='prefix', default=None, help='Destination prefix for the output.', required=True)
split_p.add_argument('-f', dest='overwrite', action='store_true', help='Force overwrite of existing files.')

#===============================================================================
# FILTER subcommand
#
# Filter XIGT files for L,G,T lines, 1-to-1 alignment, etc.
#===============================================================================
filter_p = register_subparser(CMD_FILTER, help='Command to filter input file(s) for instances')

filter_p.add_argument(ARG_INFILE, nargs='+', help='XIGT files to filter.', type=globfiles)
filter_p.add_argument(ARG_OUTFILE, help="Output file (Combines from inputs)")
filter_p.add_argument('--require-lang', help='Require instances to have language line', action='store_true', default=False)
filter_p.add_argument('--require-gloss', help='Require instances to have gloss line', action='store_true', default=False)
filter_p.add_argument('--require-trans', help='Require instances to have trans line', action='store_true', default=False)
filter_p.add_argument('--require-gloss-pos', help='Require instance to have gloss pos tags', action='store_true', default=False)
filter_p.add_argument('--require-grammatical', help='Filter out ungrammatical instances', action='store_true', default=False)
filter_p.add_argument('--max-instances', help='Limit the number of output instances', default=0, type=int)
filter_p.add_argument('--require-aln', help='Require instances to have 1-to-1 gloss/lang alignment.', action='store_true', default=False)

#===============================================================================
# EXTRACT subcommand
#
# Extract useful things from a series of enriched XIGT-XML files, such as
# a POS classifier for the gloss line, or CFG rules from projected trees, etc.
#===============================================================================
extract_p = register_subparser(CMD_EXTRACT, help='Command to extract data from enriched XIGT-XML files')

extract_p.add_argument('FILE', nargs='+', help='XIGT files to include.', type=globfiles)
extract_p.add_argument("--tagmap", dest='tagmap', help='Provide a tagset mapping to convert POS tags for this file.', type=existsfile)
extract_p.add_argument('--classifier-prefix', dest='classifier_prefix', help='Output prefix for gloss-line classifier (No extension).', default=None)
extract_p.add_argument('--tagger-prefix', dest="tagger_prefix", help='Output prefix for lang-line tagger.', default=None)
extract_p.add_argument('--cfg-rules', dest="cfg_path", help='Output path for cfg-rules.', default=None)
extract_p.add_argument('--dep-prefix', dest="dep_prefix", help='Output prefix for dependency parser', default=None)
extract_p.add_argument('--use-pos',
                       help="POS tagging method to extract for dependencies and tagger",
                       dest="pos_method",
                       choices=ARG_POS_EXTRACT_METHODS,
                       default=ARG_POS_ANY)
extract_p.add_argument('--use-align', dest="aln_method",
                       help="Alignment method to use for extracting projected items, or heuristic additions to parallel sentences.",
                       choices=ARG_ALN_METHODS,
                       default=ARG_ALN_ANY)
extract_p.add_argument('--sent-prefix', dest='sent_prefix', help='Prefix with which to output parallel sentences.')
extract_p.add_argument('--sent-type', dest='sent_type', choices=[SENT_TYPE_T_G, SENT_TYPE_T_L], help="Choose between translation-gloss and translation-lang", default=SENT_TYPE_T_L)
extract_p.add_argument('--no-alignment-heur', action='store_true', help='Disable adding heuristic alignment results to aligned sentences.', default=False)

#===============================================================================
# EVAL subcommand
#
# Used for evaluating different portions of INTENT's functions against a gold-standard
# XIGT-XML file.
#===============================================================================
eval_p = register_subparser(CMD_EVAL, help='Command to eval INTENT functions against a gold-standard XIGT-XML.')

eval_p.add_argument('FILE', nargs='+', help='XIGT files to test against.', type=globfiles)
eval_p.add_argument('--classifier', help='Specify a gloss-line POS classifier to test.', type=existsfile, default=None)
eval_p.add_argument('--ds-projection', help='Evaluate DS projection methods against the gold standard DS provided in the file', action='store_true', default=False)
eval_p.add_argument('--pos-projection', help='Evaluate POS projection method against gold standard POS tags in the file.', action='store_true', default=False)
eval_p.add_argument('--alignment', help='Test alignment methods against the alignment provided in the file.', action='store_true', default=False)

#===============================================================================
# TEXT subcommand
#
# Convert three-line IGT instances in text format to XIGT-XML
#===============================================================================
text_p = register_subparser(CMD_TEXT, help="Command to convert a text document into XIGT-XML.")

text_p.add_argument('FILE', type=argparse.FileType('r', encoding='utf-8'), help='Input file')
text_p.add_argument('OUT_FILE', help='Output file')

#===============================================================================
# PROJECT subcommand
#
# (Re)do projection from an enriched instance.
#===============================================================================
project_p = register_subparser(CMD_PROJECT, help="Command that will (re)project pos/ps/ds using the specified pos source and alignment type.")

project_p.add_argument(ARG_INFILE, type=existsfile)
project_p.add_argument(ARG_OUTFILE)
project_p.add_argument('--aln-method', dest='aln_method',
                       choices=ARG_ALN_METHODS_ALL, help="The alignment method to use for projection.", default=ARG_ALN_ANY)
project_p.add_argument('--completeness', dest='completeness',
                       type=float, default=0, help="Ratio of words which must be aligned in order to project an instance.")

# Parse the args. --------------------------------------------------------------
try:
    args = main.parse_args()
except PathArgException as pae:  # If we get some kind of invalid file in the arguments, print it and exit.
    MAIN_LOG.critical(str(pae))
    # sys.stderr.write(str(pae)+'\n')
    sys.exit(2)


# Decide on action based on subcommand and args. -------------------------------

#===============================================================================
# Set verbosity level
#===============================================================================

logging.getLogger().setLevel(logging.WARNING - 10 * (min(args.verbose, 2)))

# ENRICH
if args.subcommand == CMD_ENRICH:
    enrich(**vars(args))

# STATS
elif args.subcommand == CMD_STATS:
    igt_stats(flatten_list(args.FILE), type='xigt', show_filename=True)

# SPLIT
elif args.subcommand == CMD_SPLIT:
    split_corpus(flatten_list(args.FILE), args.train, args.dev, args.test, prefix=args.prefix, overwrite=args.overwrite)

# FILTER
elif args.subcommand == CMD_FILTER:
    filter_corpus(flatten_list(getattr(args, ARG_INFILE)), getattr(args, ARG_OUTFILE), **vars(args))

# EXTRACT
elif args.subcommand == CMD_EXTRACT:
    extract_from_xigt(input_filelist = flatten_list(args.FILE), **vars(args))

# EVAL
elif args.subcommand == CMD_EVAL:
    evaluate_intent(flatten_list(args.FILE), args.classifier, args.alignment, args.ds_projection, args.pos_projection)

# TEXT CONVERT
elif args.subcommand == CMD_TEXT:
    xc = text_to_xigtxml(args.FILE)
    dump(args.OUT_FILE, xc)

elif args.subcommand == CMD_PROJECT:
    do_projection(**vars(args))

