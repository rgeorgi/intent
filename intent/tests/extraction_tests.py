from unittest import TestCase

from intent.alignment.Alignment import Alignment
from intent.consts import INTENT_ALN_GIZA, INTENT_ALN_HEUR, INTENT_ALN_HEURPOS, INTENT_ALN_GIZAHEUR, INTENT_POS_PROJ
from intent.igt.create_tiers import trans, gloss, glosses, gloss_tag_tier
from intent.igt.igt_functions import get_bilingual_alignment, get_bilingual_alignment_tier, get_trans_gloss_alignment, \
    copy_xigt, project_trans_pos_to_gloss
from intent.igt.igtutils import rgp
from intent.igt.metadata import get_intent_proj_aln_method
from intent.igt.parsing import xc_load
from intent.utils.env import xigt_testfile


class MultipleAlignmentsTest(TestCase):

    def setUp(self):
        self.xp = xigt_testfile('multiple_alignments.xml')
        self.xc = xc_load(self.xp)


    def test_align_extract(self):
        inst = copy_xigt(self.xc[0])
        # rgp(get_bilingual_alignment_tier(inst, trans(inst).id, glosses(inst).id, aln_method=INTENT_ALN_HEURPOS))
        aheur = get_trans_gloss_alignment(inst, aln_method=INTENT_ALN_HEUR)
        aheurpos = get_trans_gloss_alignment(inst, aln_method=INTENT_ALN_HEURPOS)
        agiza = get_trans_gloss_alignment(inst, aln_method=INTENT_ALN_GIZA)
        agizaheur = get_trans_gloss_alignment(inst, aln_method=INTENT_ALN_GIZAHEUR)
        
        a1 = Alignment([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (8, 7), (11, 8)])
        a2 = Alignment([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 12), (8, 7), (9, 10), (11, 8), (12, 10), (13, 11)])
        a3 = Alignment([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 5), (7, 5), (9, 7), (10, 12), (11, 8), (12, 12), (13, 11), (14, 12)])
        a4 = Alignment([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 5), (7, 5), (9, 7), (10, 12), (11, 8), (12, 12), (13, 11), (14, 11)])

        self.assertEqual(aheur, a1)
        self.assertEqual(aheurpos, a2)
        self.assertEqual(agiza, a3)
        self.assertEqual(agizaheur, a4)


    def project_aln_select_test(self):
        inst = copy_xigt(self.xc[0])

        def test_proj_method(method):
            project_trans_pos_to_gloss(inst, aln_method=method)
            gtt = gloss_tag_tier(inst, tag_method=INTENT_POS_PROJ)
            self.assertIsNotNone(inst, gtt)
            self.assertEqual(get_intent_proj_aln_method(gtt), method)

        test_proj_method(INTENT_ALN_GIZA)
        test_proj_method(INTENT_ALN_HEUR)
        test_proj_method(INTENT_ALN_GIZAHEUR)
        test_proj_method(INTENT_ALN_HEURPOS)

        # rgp(inst)
