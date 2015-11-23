# coding=UTF-8
from os import unlink
from tempfile import NamedTemporaryFile
from unittest import TestCase

from intent.alignment.Alignment import AlignmentError, Alignment, AlignedCorpus, AlignedSent
from intent.utils.env import fast_align_bin, fast_align_atool
from intent.utils.systematizing import piperunner, ProcessCommunicator
import subprocess as sub




def fast_align_sents(e_list, f_list):
    """

    :type e_list: list[list[str]]
    :type f_list: list[list[str]]
    """


    if len(e_list) != len(f_list):
        raise AlignmentError("Input sentences of unequal length!")

    sents_f = NamedTemporaryFile(mode='w', encoding='utf-8', delete=False)

    forward_f = NamedTemporaryFile(mode='w', delete=False)

    for e_snt, f_snt in zip(e_list, f_list):
        sent = '{} ||| {}\n'.format(' '.join(e_snt), ' '.join(f_snt))
        sents_f.write(sent)
    sents_f.close()

    # -------------------------------------------
    # Callback function to write out the alignments
    # to a file.
    # -------------------------------------------

    def write_alignments(moses_aln_str, aln_f):
        aln_f.write(moses_aln_str+'\n')


    # -------------------------------------------
    # Callback function to parse the moses-style alignments to 1-indexed
    # -------------------------------------------
    alignments = []
    def parse_alignments(aln):
        a = Alignment()
        for pair in aln.split():
            i, j = pair.split('-')
            a.add((int(i)+1, int(j)+1))
        alignments.append(a)

    # -------------------------------------------
    # Set up the default args...
    args = [fast_align_bin, '-i', sents_f.name, '-v', '-d']

    p = ProcessCommunicator(args, stdout_func=parse_alignments)
    p.wait()
    forward_f.close()   # Close the file handle so it's flushed...


    # -------------------------------------------
    # 4) Delete all the files...
    unlink(forward_f.name)
    unlink(sents_f.name)

    return alignments



class FastAlignTest(TestCase):

    def basic_test(self):
        en_sents = [['the','house','is','blue'],
                    ['i','live','in','a','big','haus'],
                    ['a', 'cat', 'live', 'in', 'the', 'house']]
        de_sents = [['das', 'haus', 'ist', 'blau'],
                    ['ich','in','eine','groß','haus','leben'],
                    ['eine', 'katze', 'leben', 'in', 'dem', 'haus']]
        aln = fast_align_sents(en_sents, de_sents)

        my_aln = [Alignment({(4, 4), (1, 1), (3, 3), (2, 2)}),
                  Alignment({(3, 2), (5, 5), (6, 6), (4, 4), (4, 3), (1, 1)}),
                  Alignment({(5, 5), (3, 3), (6, 6), (4, 4), (2, 2), (1, 1)})]


        # print(aln)
        self.assertEqual(aln, my_aln)
