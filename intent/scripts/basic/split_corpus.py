import logging
import os
from xigt.codecs import xigtxml

SPLIT_LOG = logging.getLogger('SPLIT')

from intent.igt.rgxigt import RGCorpus

__author__ = 'rgeorgi'

class CorpusSplitException(Exception): pass

class WordCount():
    """
    Quick class to keep track of words, and the sentences
    to which they belong, so that when we ask for a certain
    word number, we can quickly figure out in which that sentence
    that word belongs.
    """
    def __init__(self):
        self.total = 0
        self._word_dict = {}
        self._sent_dict = {}



    def add(self, snt_num, num_words):

        for i in range(num_words):
            self._word_dict[i+self.total] = snt_num
            self.total += 1

        self._sent_dict[snt_num] = num_words

    def get_snt_from_wordnum(self, wordnum):
        """
        Given the index of a word in the corpus,
        return the sentence to which it belongs.

        :rtype : int
        :param wordnum: The index of the word
        :type wordnum: int
        """
        return self._word_dict[wordnum]

    @property
    def num_snts(self):
        return len(self._sent_dict.keys())

    @property
    def num_words(self):
        return self.total


def split_corpus(filelist, train=0.8, dev=0.1, test=0.1, prefix='', overwrite=False):

    instances = []

    # -- 0) Initialize the counter to keep track of which word index
    #       is in which sentence.
    wc = WordCount()

    # -- 1) Load all the files
    for f in filelist:
        SPLIT_LOG.info("Processing file {}".format(f))
        xc = RGCorpus.load(f)
        for i, inst in enumerate(xc):
            instances.append(inst)

            num_words = len(inst.lang)
            SPLIT_LOG.debug('{} words in sentence {} (id {})'.format(num_words, i, inst.id))
            wc.add(i, len(inst.lang))

    # -- 2) Figure out the number of words.
    num_train_words = round(train * wc.num_words)
    num_dev_words   = round(dev   * wc.num_words)
    num_test_words  = round(test  * wc.num_words)

    # -- 3) Get the word indices.
    train_word_index = num_train_words
    dev_word_index   = train_word_index + num_dev_words
    test_word_index  = dev_word_index   + num_test_words

    # -- 4) Figure out which sentence indices these refer to.
    train_sent_index = wc.get_snt_from_wordnum(train_word_index)
    dev_sent_index   = wc.get_snt_from_wordnum(dev_word_index)
    test_sent_index  = wc.get_snt_from_wordnum(test_word_index)

    # -- 4) Now, split up the data.

    train_instances = instances[0:train_sent_index]
    dev_instances   = instances[train_sent_index:dev_sent_index]
    test_instances  = instances[dev_sent_index:test_sent_index+1]

    # -- 5) Create the output file names.
    train_path = outpath_name(prefix, 'train')
    dev_path   = outpath_name(prefix, 'dev')
    test_path  = outpath_name(prefix, 'test')

    # -- 6) Write out the output files.
    write_instances(train_instances, train_path, 'train')
    write_instances(dev_instances, dev_path, 'dev')
    write_instances(test_instances, test_path, 'test')

def outpath_name(prefix, type):
    if prefix:
        return prefix + '_{}.xml'.format(type)
    else:
        return prefix + '{}.xml'.format(type)


def write_instances(instance_list, out_path, type, overwrite=False):

    if os.path.exists(out_path) and not overwrite:
        SPLIT_LOG.error('File "{}" already exists and overwrite flag not set. Skipping!'.format(out_path))
        return
    else:

        if not os.path.exists(os.path.dirname(out_path)):
            os.makedirs(os.path.dirname(out_path))


        num_sents = len(instance_list)
        if num_sents > 0:
            xc = RGCorpus()
            for i in instance_list:
                xc.append(i)

            print("Writing {} instances to {}...".format(num_sents, out_path))
            f = open(out_path, 'w', encoding='utf-8')
            xigtxml.dump(f, xc)
            f.close()
        else:
            SPLIT_LOG.warn("No instances allocated for {}. Skipping file.".format(type))


