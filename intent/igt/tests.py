'''
Created on Feb 24, 2015

:author: rgeorgi <rgeorgi@uw.edu>
'''
from unittest import TestCase
from intent.igt.rgxigt import RGCorpus, GlossLangAlignException, RGIgt, rgp
from intent.alignment.Alignment import Alignment
from intent.utils.env import c, posdict, classifier, tagger_model, xigt_dir
import pickle
from intent.interfaces.mallet_maxent import MalletMaxent
from intent.interfaces.stanford_tagger import StanfordPOSTagger
import os


xc = RGCorpus.loads('''<xigt-corpus>
<igt id="i2" doc-id="28.txt" tag-types="L+AC B G B T" line-range="487 491">
  <metadata type="xigt-meta">
    <meta type="language" iso-639-3="eng" tiers="glosses translations" name="english"/>
  </metadata>
  <tier id="r" type="odin" state="raw">
    <item id="r1" line="487" tag="L+AC">  (12).                   Las mujeres tenemos esperanza. (Jelinek 1984:48)</item>
    <item id="r2" line="488" tag="B"/>
    <item id="r3" line="489" tag="G">                          the women have-PRES-1plur hope</item>
    <item id="r4" line="490" tag="B"/>
    <item id="r5" line="491" tag="T">                          "We women have hope."</item>
  </tier>
  <tier id="c" type="odin" alignment="r" state="clean">
    <item id="c1" alignment="r1" tag="L+AC">  (12).                   Las mujeres tenemos esperanza. (Jelinek 1984:48)</item>
    <item id="c2" alignment="r2" tag="B"/>
    <item id="c3" alignment="r3" tag="G">                          the women have-PRES-1plur hope</item>
    <item id="c4" alignment="r4" tag="B"/>
    <item id="c5" alignment="r5" tag="T">                          "We women have hope."</item>
  </tier>
  <tier id="n" type="odin" alignment="c" state="normalized">
    <item id="n1" alignment="r1" tag="L">Las mujeres tenemos esperanza Jelinek 1984:48</item>
    <item id="n2" alignment="r3" tag="G">the women have-PRES-1plur hope</item>
    <item id="n3" alignment="r5" tag="T">We women have hope</item>
  </tier>
  <tier id="t" type="translations" content="n">
    <item id="t1" content="n3"/>
  </tier>
  <tier id="tw" type="translation-words" segmentation="t">
    <item id="tw1" segmentation="t1[0:2]"/>
    <item id="tw2" segmentation="t1[3:8]"/>
    <item id="tw3" segmentation="t1[9:13]"/>
    <item id="tw4" segmentation="t1[14:18]"/>
  </tier>
  <tier id="g" type="gloss-phrases" content="n">
    <item id="g1" content="n2"/>
  </tier>
  <tier id="gw" type="gloss-words" segmentation="g">
    <item id="gw1" segmentation="g1[0:3]"/>
    <item id="gw2" segmentation="g1[4:9]"/>
    <item id="gw3" segmentation="g1[10:25]"/>
    <item id="gw4" segmentation="g1[26:30]"/>
  </tier>
  <tier id="p" type="phrases" content="n">
    <item id="p1" content="n1"/>
  </tier>
  <tier id="w" type="words" segmentation="p">
    <item id="w1" segmentation="p1[0:3]"/>
    <item id="w2" segmentation="p1[4:11]"/>
    <item id="w3" segmentation="p1[12:19]"/>
    <item id="w4" segmentation="p1[20:29]"/>
    <item id="w5" segmentation="p1[30:37]"/>
    <item id="w6" segmentation="p1[38:45]"/>
  </tier>
  <tier id="gm" type="glosses" content="gw">
    <item id="gm1" content="gw1[0:3]"/>
    <item id="gm2" content="gw2[0:5]"/>
    <item id="gm3" content="gw3[0:4]"/>
    <item id="gm4" content="gw3[5:9]"/>
    <item id="gm5" content="gw3[10:15]"/>
    <item id="gm6" content="gw4[0:4]"/>
  </tier>
  <tier id="m" type="morphemes" content="w">
    <item id="m1" content="w1[0:3]"/>
    <item id="m2" content="w2[0:7]"/>
    <item id="m3" content="w3[0:7]"/>
    <item id="m4" content="w4[0:9]"/>
    <item id="m5" content="w5[0:7]"/>
    <item id="m6" content="w6[0:4]"/>
    <item id="m7" content="w6[5:7]"/>
  </tier>
  <tier id="tw-pos" type="pos" alignment="tw">
    <item id="tw-pos1" alignment="tw1">PRON</item>
    <item id="tw-pos2" alignment="tw2">NOUN</item>
    <item id="tw-pos3" alignment="tw3">VERB</item>
    <item id="tw-pos4" alignment="tw4">NOUN</item>
  </tier>
  <tier id="a" type="bilingual-alignments" target="gm" source="tw">
    <item id="a1" target="gm2" source="tw2"/>
    <item id="a2" target="gm3" source="tw3"/>
    <item id="a3" target="gm6" source="tw4"/>
  </tier>
  <tier id="gw-pos" type="pos" alignment="gw">
    <item id="gw-pos1" alignment="gw1">DET</item>
    <item id="gw-pos2" alignment="gw2">NOUN</item>
    <item id="gw-pos3" alignment="gw3">VERB</item>
    <item id="gw-pos4" alignment="gw4">NOUN</item>
  </tier>
</igt>
</xigt-corpus>''')

class GlossAlignTest(TestCase):
	
	def test_gloss_align(self):
		igt = xc.igts[0]
		self.assertRaises(GlossLangAlignException, igt.project_gloss_to_lang)


#===============================================================================
# Unit Tests
#===============================================================================


		
		

class TextParseTest(TestCase):
	
	def setUp(self):
		self.txt = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''
		
		self.igt = RGIgt.fromString(self.txt)
		
	
	def line_test(self):
		'''
		Test that lines are rendered correctly.
		'''
		self.assertEqual(self.igt.gloss.text(), 'I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec')
		self.assertEqual(self.igt.trans.text(), 'I made the child eat rice')
		
	def glosses_test(self):
		'''
		Test that the glosses are rendered correctly.
		'''
		self.assertEqual(self.igt.glosses.text(), 'I Nom child Dat rice Acc eat Caus Pst Dec')
		
	def word_align_test(self):
		'''
		Test that the gloss has been automatically aligned at the word level correctly.
		'''
		at = self.igt.gloss.get_aligned_tokens()
		
		self.assertEqual(at, Alignment([(1,1),(2,2),(3,3),(4,4)]))
		
	def set_align_test(self):
		'''
		Check setting alignment attributes between tiers.
		'''
		self.igt.gloss.set_aligned_tokens(self.igt.lang, Alignment([(1,1),(2,2)]))
		self.assertEqual(self.igt.gloss.get_aligned_tokens(), Alignment([(1,1),(2,2)]))
		
	def set_bilingual_align_test(self):
		'''
		Set the bilingual alignment manually, and ensure that it is read back correctly.
		'''
		
		a = Alignment([(1,1),(1,2),(2,8),(4,3),(5,7),(6,5)])
		self.igt.set_bilingual_alignment(self.igt.trans, self.igt.glosses, a)
		
		self.assertEqual(a, self.igt.get_trans_glosses_alignment())
		
class XigtParseTest(TestCase):
	'''
	Testcase to make sure we can load from XIGT objects.
	'''
	def setUp(self):
		self.xc = RGCorpus.load(os.path.join(xigt_dir, 'examples/odin/kor-ex.xml'))
		
	def xigt_load_test(self):
		pass
	
	def giza_align_test(self):
		new_c = self.xc.copy()
		new_c.giza_align_t_g()
		giza_aln = new_c[0].get_trans_glosses_alignment()
		
		giza_a = Alignment([(3, 2), (2, 8), (5, 7), (4, 3), (1, 1), (6, 5)])
		
		self.assertEquals(giza_a, giza_aln)
		
	def heur_align_test(self):
		new_c = self.xc.copy()
		new_c.heur_align()
		aln = new_c[0].get_trans_glosses_alignment()
		a = Alignment([(5, 7), (6, 5), (1, 1), (4, 3)])
		rgp(new_c)
		self.assertEquals(a, aln)
		
class CopyTest(TestCase):
		def setUp(self):
			self.txt = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''
			self.igt = RGIgt.fromString(self.txt)
			self.corpus = RGCorpus(igts=[self.igt])
			
		def test_copy(self):
			
			new_c = self.corpus.copy()
			
			self.assertNotEqual(id(self.corpus), id(new_c))
			
			# Assert that there is no alignment.
			self.assertIsNone(self.corpus.find(type='bilingual-alignments'))
			
			new_c.heur_align()
			self.assertIsNotNone(new_c.find(type='bilingual-alignments'))
			self.assertIsNone(self.corpus.find(id='bilingual-alignments'))

class POSTestCase(TestCase):
	
	def setUp(self):
		self.txt = '''doc_id=38 275 277 L G T
stage3_lang_chosen: korean (kor)
lang_code: korean (kor) || seoul (kor) || japanese (jpn) || inuit (ike) || french (fra) || malayalam (mal)
note: lang_chosen_idx=0
line=959 tag=L:   1 Nay-ka ai-eykey pap-ul mek-i-ess-ta
line=960 tag=G:     I-Nom child-Dat rice-Acc eat-Caus-Pst-Dec
line=961 tag=T:     `I made the child eat rice.\''''
		self.igt = RGIgt.fromString(self.txt)
		self.tags = ['PRON', 'NOUN', 'NOUN', 'VERB']
	
	def test_add_pos_tags(self):
		
		self.igt.add_pos_tags('gw', self.tags)
		
		self.assertEquals(self.igt.get_pos_tags('gw').tokens(), self.tags)
		
	def test_classify_pos_tags(self):
		tags = self.igt.classify_gloss_pos(MalletMaxent(classifier), posdict=posdict)
		
		self.assertEqual(tags, self.tags)
		
		
	def test_tag_trans_line(self):
		tagger = StanfordPOSTagger(tagger_model)
		self.igt.tag_trans_pos(tagger)
		