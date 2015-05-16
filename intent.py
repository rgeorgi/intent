#!/usr/bin/env python3.4

import argparse
import sys
import logging


# Start the logger and set it up. ----------------------------------------------
from intent.scripts.basic.corpus_stats import igt_stats
from intent.utils.arg_consts import PARSE_LANG_PROJ, PARSE_TRANS, POS_TYPES, PARSE_TYPES, ALN_TYPES, ALN_VAR, POS_VAR, \
    PARSE_VAR

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
    PathArgException, csv_choices

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
    igt_stats(args.FILE, type='xigt')
