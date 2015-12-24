#!/usr/bin/env python

'''
Created on Apr 30, 2014

@author: rgeorgi
'''

# Built-in Imports -------------------------------------------------------------
import logging
from argparse import ArgumentParser

# Internal Imports -------------------------------------------------------------
from intent.igt.rgxigt import RGCorpus, sort_corpus

# XIGT imports -----------------------------------------------------------------
from xigt.codecs import xigtxml

PARSELOGGER = logging.getLogger(__name__)


def parse_text(f, xigt_path):

    # 1) Build the corpus --------------------------------------------------
    corp = RGCorpus.from_txt(f.read(), require_trans=False, require_gloss=True, require_lang=True)

    # 2) load the pos dict to help classify the gloss line ---------------------
    sort_corpus(corp)
    xigtxml.dump(xigt_path, corp)


if __name__ == '__main__':

    p = ArgumentParser()
    p.add_argument('-i', '--input', required=True, help='Input text file to convert to annotated xigt.')
    p.add_argument('-o', '--output', required=True, help='Output xigt path.')

    args = p.parse_args()

    parse_text(args.input, args.output)