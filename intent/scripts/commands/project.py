# -------------------------------------------
# (Re)do POS and parse projection from a file that
# already has alignment and
# -------------------------------------------
from intent.igt.alignment import heur_align_inst
from intent.igt.exceptions import NoTransLineException, NoNormLineException, MultipleNormLineException
from intent.igt.search import lang, gloss
from xigt.codecs import xigtxml

from intent.consts import *
from xigt.consts import INCREMENTAL


def do_projection(**kwargs):
    IN_FILE = kwargs.get(ARG_INFILE)
    with open(IN_FILE, 'r', encoding='utf-8') as f:
        xc = xigtxml.load(f, mode=INCREMENTAL)
        for inst in xc:
            print(inst)
            try:
                heur_align_inst(inst)
            except (NoNormLineException, MultipleNormLineException) as ntle:
                pass

        with open(kwargs.get(ARG_OUTFILE), 'w', encoding='utf-8') as out_f:
            xigtxml.dump(out_f, xc)
