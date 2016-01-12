import logging
import os
from unittest import TestCase

from intent.igt.consts import ODIN_LANG_TAG, ODIN_JUDGMENT_ATTRIBUTE, ODIN_TRANS_TAG
from xigt.codecs import xigtxml

from intent.igt.rgxigt import RGCorpus, retrieve_normal_line, retrieve_lang_phrase_tier, retrieve_trans_phrase
from intent.interfaces.stanford_parser import StanfordParser
from intent.subcommands import enrich
from intent.trees import DepTree, DEPSTR_PTB, project_ds
from intent.utils.arg_consts import PARSE_VAR, PARSE_LANG_PROJ, ALN_VAR, ALN_HEUR, PARSE_TRANS, POS_VAR, POS_LANG_CLASS, \
    POS_LANG_PROJ
from intent.utils.env import testfile_dir, classifier

__author__ = 'rgeorgi'


ctn_file = os.path.join(testfile_dir, 'xigt/ctn2-xigt.xml')
ger_file = os.path.join(testfile_dir, 'xigt/single_ger.xml')
kor_file = os.path.join(testfile_dir, 'xigt/kor-ex.xml')


# Some of the tree test files.
xigt_proj = os.path.join(testfile_dir, 'xigt/xigt-projection-tests.xml')
ds_cycle  = os.path.join(testfile_dir, 'xigt/ds-cycle-test.xml')

no_enrich_args = {'OUT_FILE':'/dev/null'}
all_enrich_args = {'OUT_FILE':'/dev/null',
                   'class_path':classifier,
                   POS_VAR:[POS_LANG_CLASS, POS_LANG_PROJ],
                   PARSE_VAR:[PARSE_LANG_PROJ, PARSE_TRANS],
                   ALN_VAR:[ALN_HEUR]}

class ParseTests(TestCase):

    def test_ctn(self):
        enrich(IN_FILE=ctn_file, **no_enrich_args)

    def test_kor(self):
        enrich(IN_FILE=kor_file, **no_enrich_args)

    def test_ger(self):
        enrich(IN_FILE=ger_file, **no_enrich_args)

class ReadTreeTests(TestCase):
    """
    Unit tests to ensure that trees are read correctly from XIGT.
    """

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.xc = RGCorpus.load(xigt_proj, basic_processing=True)
        self.inst1 = self.xc[0]
        self.inst2 = self.xc[1]

    def test_read_ds_tree(self):
        ds = self.inst1.get_ds(self.inst1.trans)
        r = DepTree.fromstring("""(ROOT[0] (found[2] (Someone[1]) (them[3]) (boring[4])))""", stype=DEPSTR_PTB)

        self.assertTrue(r.structurally_eq(ds))

    def test_project_ds_tree(self):
        """
        Test that performing projection works correctly.
        """
        self.inst1.project_ds()
        self.inst2.project_ds()



    def test_read_proj_ds_tree(self):
        src_t = self.inst2.get_ds(self.inst2.trans)
        tgt_w = self.inst2.lang
        aln   = self.inst2.get_trans_gloss_lang_alignment()

        tgt_t = DepTree.fromstring("""
        (ROOT[0]
            (glaubst[2]
                (Was[1])
                (Du[3])
                (wer[4])
                (angerufen[5] (hat[6]))
            ))
        """, stype=DEPSTR_PTB)

        proj_t = project_ds(src_t, tgt_w, aln)

        self.assertTrue(proj_t.structurally_eq(tgt_t))

    def test_conll(self):
        ds = self.inst2.get_lang_ds()
        conll_str = ds.to_conll()

        s = """
1	Was	Was	PRON	PRON	_	2	_	_	_
2	glaubst	glaubst	VERB	VERB	_	0	root	_	_
3	Du	Du	PRON	PRON	_	2	nsubj	_	_
4	wer	wer	PRON	PRON	_	2	dobj	_	_
5	angerufen	angerufen	VERB	VERB	_	2	dep	_	_
6	hat	hat	VERB	VERB	_	5	_	_	_"""

        self.assertEqual(conll_str.strip(), s.strip())


    def test_ds_cycle(self):
        """
        The tree in the ds_cycle file has "woman" depend both
        on "arriving" and "browse."
        """
        xc = RGCorpus.load(ds_cycle)
        inst = xc[0]

        #  1    2       4        5       7    8    9
        # The woman, (after) arriving, began to browse.

        # (The commas count as words, hence the skipping)

        tgt_t = DepTree.fromstring("""
        (ROOT[0]
            (began[7]
                (woman[2]
                    (The[1])
                    (\(after\)[4] (arriving[5])))
                (browse[9]
                    (woman[2])
                    (to[8])
                )
            ))
        """, stype=DEPSTR_PTB)

        ds = inst.get_ds(inst.trans)
        self.assertTrue(tgt_t.structurally_eq(ds))

        self.assertIsNone(inst.project_ds())

class UnknownErrorTests(TestCase):

    def test_ds_project(self):
        sp = StanfordParser()

        xc = RGCorpus.load(os.path.join(testfile_dir, 'xigt/index_error.xml'), basic_processing=True)
        inst = xc[0]
        inst.heur_align()
        inst.parse_translation_line(sp, dt=True)
        inst.project_ds()
        proj_t = inst.get_lang_ds()

        tgt_t = DepTree.fromstring("""(ROOT[0]
                                        (salli-i[2]
                                            (Jumala[1])
                                            (sata-a[3])
                                            (rake-i-ta[4])
                                            (ja[5])
                                            (tuhka-a[6]) ))""", stype=DEPSTR_PTB)

        self.assertTrue(tgt_t.similar(proj_t))

        inst2 = xc[1]
        inst2.heur_align()
        inst2.parse_translation_line(sp, dt=True)
        inst2.project_ds()

        tgt2_t = DepTree.fromstring("""(ROOT[0]
                                            (unohta-a[2] (*Minua[1])
                                                (unohda-n[4]
                                                    (/Minä[3])
                                                    (/laula-tta-a[6] (pelo-tta-a[5]))
                                                )
                                            ))
                                        """, stype=DEPSTR_PTB)

        self.assertTrue(inst2.get_lang_ds(), tgt2_t)

    def harness(self, name):
        d = all_enrich_args.copy()
        d['IN_FILE'] = os.path.join(testfile_dir, name)
        self.assertIsNone(enrich(**d))

    def test_3191(self):
        self.harness('xigt/3191.xml')

    def test_3294(self):
        self.harness('xigt/3294.xml')

    def test_3307(self):
        self.harness('xigt/3307.xml')

    def test_555(self):
        self.harness('xigt/555.xml')


class MultipleLineTests(TestCase):

    def test_911(self):
        d = all_enrich_args.copy()
        d['IN_FILE'] = os.path.join(testfile_dir, 'xigt/multiple_lang_lines.xml')
        self.assertIsNone(enrich(**d))

class DepTreeTests(TestCase):

    def test_814(self):
        d = all_enrich_args.copy()
        d['IN_FILE'] = os.path.join(testfile_dir, 'xigt/814.xml')
        self.assertIsNone(enrich(**d))

