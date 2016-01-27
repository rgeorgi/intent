from unittest import TestCase

from intent.consts import DATA_PROV, DATA_SRC, INTENT_META_SOURCE, DATA_METH, INTENT_ALN_GIZA, \
    WORDS_TYPE, GLOSS_WORD_TYPE, INTENT_GLOSS_WORD, INTENT_GLOSS_MORPH
from intent.igt.metadata import set_meta_attr, find_meta, find_meta_attr, get_meta_timestamp, timestamp_meta, is_contentful_meta, \
    del_meta_attr
from intent.igt.rgxigt import RGTier, RGIgt, is_word_level_gloss, add_word_level_info
from xigt import Meta, Metadata


__author__ = 'rgeorgi'

class ProvenanceTest(TestCase):

    def setUp(self):
        self.t = RGTier(id='t')
        self.metadata = []

    def add_meta_test(self):
        set_meta_attr(self.t, DATA_PROV, DATA_SRC, INTENT_META_SOURCE)
        set_meta_attr(self.t, DATA_PROV, DATA_METH, INTENT_ALN_GIZA)

        self.assertEqual(find_meta_attr(self.t, DATA_PROV, DATA_METH), INTENT_ALN_GIZA)
        self.assertEqual(find_meta_attr(self.t, DATA_PROV, DATA_SRC), INTENT_META_SOURCE)

        self.assertEqual(len(self.t.metadata), 1)
        self.assertEqual(len(self.t.metadata[0].metas), 1)

    def timestamp_test(self):
        set_meta_attr(self.t, DATA_PROV, DATA_SRC, INTENT_META_SOURCE)

        self.assertIsNotNone(get_meta_timestamp(find_meta(self.t, DATA_PROV)))

class WordTypeTest(TestCase):
    def setUp(self):
        self.i = RGIgt(id='i1')
        self.w = RGTier(id='w', type=WORDS_TYPE)
        self.gw =RGTier(id='gw', type=GLOSS_WORD_TYPE, alignment=self.w.id)

        self.i.extend([self.w, self.gw])

    def test_wo_metadata(self):
        self.assertTrue(is_word_level_gloss(self.gw))

    def test_w_metadata(self):
        self.gw.alignment = None
        self.assertFalse(is_word_level_gloss(self.gw))

        add_word_level_info(self.gw, INTENT_GLOSS_WORD)
        self.assertTrue(is_word_level_gloss(self.gw))

        add_word_level_info(self.gw, INTENT_GLOSS_MORPH)
        self.assertFalse(is_word_level_gloss(self.gw))

class ContentfulMeta(TestCase):
    def setUp(self):
        self.m1 = Meta(text='Something')
        self.m2 = Meta(attributes={'Something':'test'})
        self.m3 = Meta()
        timestamp_meta(self.m3)
        self.m4 = Meta()

    def content_test(self):
        self.assertTrue(is_contentful_meta(self.m1))
        self.assertTrue(is_contentful_meta(self.m2))
        self.assertFalse(is_contentful_meta(self.m3))
        self.assertFalse(is_contentful_meta(self.m4))

class DelMetaTests(TestCase):
    def setUp(self):
        self.t = RGTier()
        self.md = Metadata()
        self.t.metadata = [self.md]

        self.m1 = Meta(text='foo')
        self.m2 = Meta(type='foobar', attributes={'foo':'bar'})

    def no_meta_remains_test(self):
        self.md.append(self.m2)

        self.assertEqual(len(self.t.metadata), 1)
        self.assertEqual(len(self.md), 1)
        del_meta_attr(self.t, 'foobar', 'foo')

        self.assertEqual(len(self.md), 0)
        self.assertEqual(len(self.t.metadata), 0)

    def meta_remains_test(self):
        self.md.append(self.m1)
        self.md.append(self.m2)

        self.assertEqual(len(self.t.metadata), 1)
        self.assertEqual(len(self.md), 2)

        del_meta_attr(self.t, 'foobar', 'foo')

        self.assertEqual(len(self.t.metadata), 1)
