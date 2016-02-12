#!/usr/bin/env python3
# -------------------------------------------
# Script to evaluate dependency parser
# -------------------------------------------
import logging
import os
import sys
from argparse import ArgumentParser

from intent.corpora.conll import ConllCorpus, eval_conll_paths
from intent.interfaces.mst_parser import MSTParser
from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.utils.argutils import existsfile

LOG = logging.getLogger('DEPENDENCIES')


def eval_mst(model_path, test_path, out_prefix, lowercase=True, tagger=None, force=False, result_strem=None):
    mp = MSTParser()

    # -------------------------------------------
    # Use the output prefix to create some new files.
    # -------------------------------------------
    eval_path = out_prefix + '_eval_tagged.txt'
    out_path  = out_prefix + '_out_tagged.txt'


    # -------------------------------------------
    # Rewrite the test file; POS tag the data
    # with the POS tags from our tagger,
    # and strip features.
    # -------------------------------------------
    if not os.path.exists(eval_path) or force:
        LOG.log(1000, "")
        cc = ConllCorpus.read(test_path)
        if lowercase:
            cc.lower()
        cc.strip_tags()
        cc.strip_feats()
        if tagger is not None:
            LOG.log(1000, "POS Tagging evaluation ")
            cc.tag(StanfordPOSTagger(tagger))
        os.makedirs(os.path.dirname(eval_path), exist_ok=True)
        cc.write(eval_path)
    # -------------------------------------------


    mp.test(model_path, eval_path, out_path)
    eval_conll_paths(test_path, out_path)


if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('CMD', choices=['train', 'test'])
    p.add_argument('-p', '--parser', help='Parser model file')
    p.add_argument('-t', '--tagger', help='Tagger model file')
    p.add_argument('--test', help='Testing file in CoNLL Format', type=existsfile)
    p.add_argument('--train', help='Training file in CoNLL format', type=existsfile)
    p.add_argument('-o', '--output', help="Output prefix", default=None, required=True)
    p.add_argument('-f', '--force', help='Force overwrite of precursor files', default=False, action='store_true')

    args = p.parse_args()

    # -------------------------------------------
    # Sanity check the arguments
    # -------------------------------------------
    if args.CMD == 'test':
        if args.parser is None or args.test is None:
            print("\nERROR: --model and --test args are required for test CMD.\n")
            p.print_help()
            sys.exit(1)
        elif not os.path.exists(args.parser):
            LOG.error('Error: parser file "{}" does not exist.'.format(args.parser))
            sys.exit(1)
        elif not os.path.exists(args.test):
            LOG.error('Error: eval file "{}" does not exist.'.format(args.parser))
            sys.exit()

        LOG.log(1000, "Beginning test of parser...")
        eval_mst(args.parser, args.test, args.output, tagger=args.tagger)
    elif args.CMD == 'train':
        if args.train is None or args.parser is None:
            print("\nERROR: --train and --model args are required for train CMD.")
            p.print_help()
            sys.exit(1)
        mp = MSTParser()
        mp.train(args.train, args.parser)