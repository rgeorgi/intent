#!/usr/bin/env python3
from argparse import ArgumentParser

import common

from intent.consts import RAW_STATE
from intent.igt.igt_functions import delete_tier
from intent.igt.parsing import xc_load
from intent.igt.references import xigt_findall
from xigt import Tier
from xigt.codecs import xigtxml


def strip_enrichment(inpath, outpath):
    xc = xc_load(inpath)
    for inst in xc:
        f = lambda x: (isinstance(x, Tier) and
                       (x.type != ODIN_TIER_TYPE or
                        x.attributes.get(STATE_ATTRIBUTE) != RAW_STATE))
        not_raw_tiers = xigt_findall(inst, others=[f])
        for not_raw_tier in not_raw_tiers:
            delete_tier(not_raw_tier)

    with open(outpath, 'w') as f:
        xigtxml.dump(f, xc)


from intent.consts import ARG_INFILE, ARG_OUTFILE, ODIN_TIER_TYPE, STATE_ATTRIBUTE

if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument(ARG_INFILE)
    p.add_argument(ARG_OUTFILE)

    args = vars(p.parse_args())

    strip_enrichment(args[ARG_INFILE], args[ARG_OUTFILE])