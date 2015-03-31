#!/usr/bin/env python3.4

import argparse, os, sys
import logging
from intent.utils.ConfigFile import ConfigFile
from telnetlib import theNULL

# Start the logger and set it up. ----------------------------------------------
logging.basicConfig(format=logging.BASIC_FORMAT)
MAIN_LOG = logging.getLogger('INTENT')

#===============================================================================
# Check for dependencies...
#===============================================================================

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

	
#===============================================================================
# Set up the environment...
#===============================================================================

from intent.utils.env import c
from intent.utils.argutils import DefaultHelpParser, existsfile,\
	PathArgException, configfile

#===============================================================================
# Now, intialize the subcommands.
#===============================================================================



main = DefaultHelpParser(description="This is the main module for the INTENT package.",
								formatter_class=argparse.ArgumentDefaultsHelpFormatter)
main.add_argument('-c', '--config', help='Configuration file to set options for batch mode.', type=configfile)
subparsers = main.add_subparsers(help = 'Valid subcommands', dest='subcommand')


#===============================================================================
# Enrich subcommand
#===============================================================================
enrich = subparsers.add_parser('enrich', help='Enrich igt data.', 
							description='Ingest a XIGT document and add information, such as alignment, or POS tags.',
							formatter_class=argparse.ArgumentDefaultsHelpFormatter)

# Positional arguments ---------------------------------------------------------
enrich.add_argument('IN_FILE', type=existsfile, help='Input XIGT file.')
enrich.add_argument('OUT_FILE', help='Path to output XIGT file.')

# Optional arguments -----------------------------------------------------------
enrich.add_argument('-c', '--config', default=None, help='Configuration file to use for base settings (File settings will be overwritten by settngs specified here).')
enrich.add_argument('--alignment', choices=['giza','heur', 'none'], default='none',
					help="Add alignment between the translation and gloss lines using the specified method. (Required for projecting POS from translation to language lines.)")
enrich.add_argument('--pos-trans', choices=[0, 1], default=1, type=int, help='POS tag the translation line (required for projecting POS to language line.)')

enrich.add_argument('--pos-lang', choices=['proj', 'class', 'none'], default='none',
				 help='POS tag the language line using either projection (which requires a POS tagged translation line and alignment between trans and gloss)')

enrich.add_argument('--parse-trans', choices=[0,1], default=0, type=int, help='Parse the translation line for phrase structure and dependencies.')
enrich.add_argument('--project-pt', choices=[0,1], default=0, type=int, help='Project the phrase structure tree from translation to language line.')


# Parse the args. --------------------------------------------------------------
arglist = sys.argv[1:]

# The loop is here so that if we specify a config file, we can pull the subcommand out, and then 
# try the parse_args() again on the config file options.

while True:
	
	try:
		args = main.parse_args(arglist)
	except PathArgException as pae:  # If we get some kind of invalid file in the arguments, print it and exit.
		MAIN_LOG.critical(str(pae))
		#sys.stderr.write(str(pae)+'\n')
		sys.exit(2)
	else:
		if args.config:
			arglist = [args.config['COMMAND']]
			del args.config['COMMAND']
			other_args = args.config.to_arglist()
			
			arglist += other_args
			continue
		else:
			break
	
	
if args.subcommand is None:
	sys.stderr.write('A subcommand is required.\n\n')
	main.print_help()
	sys.exit(2)

# Decide on action based on subcommand and args. -------------------------------
from intent import subcommands

if args.subcommand == 'enrich':
	subcommands.enrich(**vars(args))