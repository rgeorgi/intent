#!/usr/bin/env python3.4
'''
Simple script to train an aligner for gloss and translation lines, 
picking up from a previously partially trained aligner.
'''

import logging
logging.basicConfig(level=logging.DEBUG)

import argparse
from intent.utils.argutils import existsfile
from intent.interfaces.giza import GizaAligner, Vocab, GIZA_LOG


GIZA_LOG.setLevel(logging.DEBUG)

def train_aligner(o, e, f):
    ga = GizaAligner()

    # ga = GizaAligner.load(o, e, f)
    ga.train(o, e, f)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-e', help='First language file', type=existsfile, required=True)
    p.add_argument('-f', help='Second language file', type=existsfile, required=True)
    p.add_argument('-o', help='Output prefix', required=True)

    args = p.parse_args()

    train_aligner(args.o, args.e, args.f)