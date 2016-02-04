import os
import re
from argparse import ArgumentParser

from intent.alignment.Alignment import Alignment
from intent.consts import *
from intent.igt.create_tiers import generate_normal_tier, lang, gloss, trans
from intent.igt.igt_functions import set_bilingual_alignment, create_dt_tier
from intent.igt.references import gen_tier_id, ask_item_id, normalized_tier
from intent.trees import DepEdge, Terminal, build_dep_edges, TreeError
from intent.utils.argutils import existsfile
from intent.utils.env import testfile_dir
from xigt import XigtCorpus, Igt, Tier, Item
from xigt.codecs.xigtxml import dump

__author__ = 'rgeorgi'

from unittest import TestCase

def naacl_to_xigt(naacl_path):
    """
    Convert the NAACL format to XIGT.

    :param naacl_path:
    """
    content = open(naacl_path, 'r').read()

    # First, collect all the instances.
    instances = re.findall('Igt_id[\s\S]+?Q6.*Answer', content)

    xc = XigtCorpus()

    for instance_txt in instances:
        # id = re.search('Igt_id=([\S]+)', instance_txt).group(1)
        inst = Igt(id='i{}'.format(len(xc)))

        lang_raw, gloss_raw, trans_raw = instance_txt.split('\n')[1:4]

        # Now, create the raw tier...
        raw_tier = Tier(id=gen_tier_id(inst, 'r'), type='odin', attributes={STATE_ATTRIBUTE:RAW_STATE})
        raw_tier.append(Item(id=ask_item_id(raw_tier), text=lang_raw, attributes={ODIN_TAG_ATTRIBUTE:ODIN_LANG_TAG}))
        raw_tier.append(Item(id=ask_item_id(raw_tier), text=gloss_raw, attributes={ODIN_TAG_ATTRIBUTE:ODIN_GLOSS_TAG}))
        raw_tier.append(Item(id=ask_item_id(raw_tier), text=trans_raw, attributes={ODIN_TAG_ATTRIBUTE:ODIN_TRANS_TAG}))

        inst.append(raw_tier)
        xc.append(inst)

        # Generate the clean/normal tiers, but without any cleaning.
        generate_normal_tier(inst, clean=False)

        # Lang Dependency representation handling...
        lang_ds_str = re.search('Q6:([\s\S]+?)Q6:', instance_txt).group(1)
        lang_ds_lines = lang_ds_str.split('\n')[5:-3]

        try:
            lang_dt = parse_naacl_dep(lang(inst), lang_ds_lines)
            create_dt_tier(inst, lang_dt, lang(inst), parse_method=INTENT_POS_MANUAL)
        except TreeError as te:
            pass
        except IndexError as ie:
            pass

        # Eng DS handling...
        eng_ds_str = re.search('Q3:([\s\S]+?)Q3:', instance_txt).group(1)
        eng_ds_lines = eng_ds_str.split('\n')[2:-3]

        try:
            eng_dt = parse_naacl_dep(trans(inst), eng_ds_lines)
            create_dt_tier(inst, eng_dt, trans(inst), parse_method=INTENT_POS_MANUAL)
        except TreeError as te:
            pass
        except IndexError as ie:
            pass
        except ValueError as ve:
            pass

        # Add Alignment...
        biling_aln_str = re.search('Q5:([\s\S]+?)Q5:', instance_txt).group(1)
        biling_aln_lines = biling_aln_str.split('\n')[4:-3]

        trans_offset = trans_raw.startswith(' ')
        gloss_offset = gloss_raw.startswith(' ')

        try:
            a = Alignment()
            for line in biling_aln_lines:
                gloss_s, trans_s = line.split()[0:2]

                if '.' in gloss_s:
                    continue

                gloss_i = int(gloss_s)

                for trans_token in trans_s.split(','):
                    trans_i = int(trans_token)
                    if trans_i == 0:
                        continue
                    else:
                        if trans_offset:
                            trans_i -= 1
                        if gloss_offset:
                            gloss_i -= 1
                        a.add((trans_i, gloss_i))
        except:
            pass

        set_bilingual_alignment(inst, trans(inst), gloss(inst), a, aln_method=INTENT_ALN_MANUAL)

    return xc

def parse_naacl_dep(w_tier, dep_lines):
    """
    Parse the naacl dependency representation, like:

    ::
        1 5 # Wen gesehen
        2 5 # hat gesehen
        3 5 # jeder gesehen
        4 5 # wo gesehen
        5 -1 # gesehen *TOP*
        6 5 # ? gesehen

    :param depstr:
    :type w_tier: RGTier
    """
    edges = []
    for line in dep_lines:
        dep, heads = line.split()[0:2]
        dep_w = w_tier[int(dep)-1].value()

        # Sometimes we have two heads...
        for head in heads.split(','):

            if '.' in head:
                continue

            head_i = int(head)
            if head_i == 0 or head_i == -2:
                continue
            if head_i == -1:
                head_w = 'ROOT'
                head_i = 0
            else:
                head_w = w_tier[int(head_i)-1].value()

            child_t = Terminal(dep_w, index=int(dep))
            head_t = Terminal(head_w, index=head_i)
            edges.append(DepEdge(head=head_t, dep=child_t))


    dt = build_dep_edges(edges)
    return dt

if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('IN_FILE', type=existsfile)
    p.add_argument('OUT_FILE')

    args = p.parse_args()

    xc = naacl_to_xigt(args.IN_FILE)
    dump(open(args.OUT_FILE, 'w'), xc)

class test_naacl(TestCase):

    def test_parse(self):
        p = os.path.join(testfile_dir, 'naacl/ger.naacl')
        o = os.path.join(testfile_dir, 'naacl/ger.xml')
        xc = naacl_to_xigt(p)
        dump(open(o, 'w'), xc)