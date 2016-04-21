#!/usr/bin/env python3
from argparse import ArgumentParser
from collections import defaultdict

import common
import re

from intent.alignment.Alignment import Alignment, AlignPair
from intent.consts import punc_re_mult
from intent.eval.AlignEval import AlignEval
from intent.igt.igtutils import split_punctuation
from intent.interfaces.giza import GizaAligner


def load_snts(path, limit=None, last_n=None):
    snts = []
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        num_lines = len(lines)
        for i, line in enumerate(lines):

            if line.startswith('<s snum'):
                txt = re.search('<s snum=[0-9]+>\s*(.*?)\s*</s>', line).group(1).lower()
            else:
                txt = line.lower()

            if True:
                txt = split_punctuation(txt)

            if (limit is None) or (limit is not None and i < limit) or (last_n is not None and i >= num_lines-last_n):
                snts.append(txt.split())

    return snts

def load_aln(path):
    alns = defaultdict(lambda: Alignment())
    with open(path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            sent_num, e_num, f_num, p_s = line.split()
            sent_num = int(sent_num)
            e_num = int(e_num)
            f_num = int(f_num)

            # Only add if we are accepting probable
            # alignments, or it is a sure alignment.
            aln = alns[sent_num]
            ap = AlignPair((e_num, f_num), type=p_s.lower())
            aln.add(ap)

    return [alns[i] for i in sorted(alns.keys())]

if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('-e')
    p.add_argument('-f')
    p.add_argument('--gold-e', default=None)
    p.add_argument('--gold-f', default=None)
    p.add_argument('--gold-aln', default=None)
    p.add_argument('--limit', default=None, type=int)

    args = p.parse_args()

    last_n = None
    if args.gold_aln:
        gold_alns = load_aln(args.gold_aln)
        last_n = len(gold_alns)

    e_snts = load_snts(args.e, args.limit)
    f_snts = load_snts(args.f, args.limit)
    assert len(e_snts) == len(f_snts)

    gold_e_snts = load_snts(args.gold_e)
    gold_f_snts = load_snts(args.gold_f)

    ga = GizaAligner()
    test_alns = ga.temp_train(e_snts+gold_e_snts, f_snts+gold_f_snts)

    if args.gold_aln:
        assert len(e_snts+gold_e_snts) >= len(gold_alns)

        # -------------------------------------------
        # We will assume that the test sentences are the last
        # in the file.
        # -------------------------------------------

        alns_to_test = test_alns[-len(gold_alns):]
        assert len(alns_to_test) == len(gold_alns)

        ae = AlignEval(alns_to_test, gold_alns)
        print(','.join([str(args.limit)]+['{:.5f}'.format(f) for f in ae.all()]))


