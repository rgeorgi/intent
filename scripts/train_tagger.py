#!/usr/bin/env python3
# =============================================================================
# This script will train a POS tagger given either a slashtagged
# input file, or a CONLL input file, and optionally take a tagmap file
# to convert the
# =============================================================================
import common
from argparse import ArgumentParser
from tempfile import NamedTemporaryFile
from os import unlink
import logging
logging.basicConfig(level=logging.INFO)


from intent.corpora.POSCorpus import POSCorpus
from intent.corpora.conll import ConllCorpus
from intent.interfaces import stanford_tagger


def train_tagger(prefix, slashtags=[], conll=[], tagmap = None, lowercase=False):



    trainsents = []

    for c in conll:
        cc = ConllCorpus.read(c, lowercase=lowercase, tagmap=tagmap)
        for sent in cc:
            trainsents.append(sent.slashtags())

    for st in slashtags:
        raise NotImplementedError

    alldatatrain = NamedTemporaryFile('w', delete=False)

    # -------------------------------------------
    # Now write all the training sentences out to the temporary file.
    # -------------------------------------------
    for trainsent in trainsents:
        alldatatrain.write(trainsent+'\n')
    alldatatrain.close()

    # -------------------------------------------
    # And train the tagger.
    # -------------------------------------------
    r = stanford_tagger.train_postagger(alldatatrain.name, prefix+'.tagger')
    unlink(alldatatrain.name)

if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('--slashtags', nargs='+', default=[], help='Slashtag-format input file.')
    p.add_argument('--conll', nargs='+', default=[], help='CoNLL-formatted input file.')
    p.add_argument('--tagmap', help='Optional tagset remapping file')
    p.add_argument('--prefix', help='Output path for the model file.', required=True)

    args = p.parse_args()

    train_tagger(args.prefix, args.slashtags, args.conll, args.tagmap)