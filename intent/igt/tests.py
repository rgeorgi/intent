'''
Created on Feb 24, 2015

:author: rgeorgi <rgeorgi@uw.edu>
'''
import unittest
from xigt.codecs import xigtxml
from igt.rgxigt import RGCorpus, rgp, GlossLangAlignException


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

class GlossAlignTest(unittest.TestCase):
	
	def test_gloss_align(self):
		igt = xc.igts[0]
		self.assertRaises(GlossLangAlignException, igt.project_gloss_to_lang)

		