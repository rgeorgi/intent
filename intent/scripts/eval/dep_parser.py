#!/usr/bin/env python3
# -------------------------------------------
# Script to evaluate dependency parser
# -------------------------------------------
from argparse import ArgumentParser
from tempfile import NamedTemporaryFile

from os import unlink

import sys

from intent.interfaces.mst_parser import MSTParser
from intent.utils.argutils import existsfile


def eval_mst(model_path, test_path, out_path=None, lowercase=True):
    mp = MSTParser()

    # Get the output file name...
    if out_path is None:
        out_f = NamedTemporaryFile('w', delete=False)
        out_f.close()
        out_path = out_f.name

    # -------------------------------------------
    # Rewrite the test file with lowercase
    # Tokens
    # -------------------------------------------
    if lowercase:
        test_lower_f = NamedTemporaryFile('w', delete=False)
        test_lower_path = test_lower_f.name
        with open(test_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    token = line.split()[0].lower()
                    rest  = line.split()[1:]
                    test_lower_f.write('\t'.join([token]+rest)+'\n')
                else:
                    test_lower_f.write(line)
        test_lower_f.close()
        test_path = test_lower_path


    mp.test(model_path, test_path, out_path)
    mp.eval(test_path, out_path)

    if out_path is None:
        unlink(out_path)
    if lowercase:
        unlink(test_lower_path)

if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('CMD', choices=['train', 'test'])
    p.add_argument('-m', '--model', help='Parser model file')
    p.add_argument('--test', help='Testing file in CoNLL Format', type=existsfile)
    p.add_argument('--train', help='Training file in CoNLL format', type=existsfile)
    p.add_argument('-o', '--output', help="Save the output file", default=None)

    args = p.parse_args()

    if args.CMD == 'test':
        if args.model is None or args.test is None:
            print("\nERROR: --model and --test args are required for test CMD.\n")
            p.print_help()
            sys.exit(1)
        eval_mst(args.model, args.test, args.output)
    elif args.CMD == 'train':
        if args.train is None or args.model is None:
            print("\nERROR: --train and --model args are required for train CMD.")
            p.print_help()
            sys.exit(1)
        mp = MSTParser()
        mp.train(args.train, args.model)