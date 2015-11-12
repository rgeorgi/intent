from os import unlink
from tempfile import NamedTemporaryFile
from unittest import TestCase

from intent.alignment.Alignment import AlignmentError, Alignment, AlignedCorpus, AlignedSent
from intent.utils.env import fast_align_bin, fast_align_atool
from intent.utils.systematizing import piperunner, ProcessCommunicator
import subprocess as sub




def fast_align_sents(e_list, f_list, symmetric=True):
    """

    :type e_list: list[list[str]]
    :type f_list: list[list[str]]
    """


    if len(e_list) != len(f_list):
        raise AlignmentError("Input sentences of unequal length!")

    sents_f = NamedTemporaryFile(mode='w', encoding='utf-8', delete=False)

    forward_f = NamedTemporaryFile(mode='w', delete=False)
    reverse_f = NamedTemporaryFile(mode='w', delete=False)

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
    # 2) Set up which function to use for the first step.
    #    (a) If we are doing symmetric alignment, we will
    #        want to save the output of our alignment to a file and then run reverse.
    #    (b) If we aren't doing symmetric alignment, just
    #        parse the results of the unidirectional alignment
    #        and use that.

    if not symmetric:
        forward_func = parse_alignments
    else:
        forward_func = lambda x: write_alignments(x, forward_f)

    # -------------------------------------------
    # Set up the default args...
    args = [fast_align_bin, '-i', sents_f.name, '-v', '-d']

    p = ProcessCommunicator(args, stdout_func=forward_func)
    p.wait()
    forward_f.close()   # Close the file handle so it's flushed...

    # -------------------------------------------
    # 3) If we are doing symmetric alignment, run the
    #    reverse alignment...

    if symmetric:
        p = ProcessCommunicator(args+['-r'], stdout_func = lambda x: write_alignments(x, reverse_f))
        p.wait()

        reverse_f.close() # Close the file handle...

        # -------------------------------------------
        # Now, let's do the grow-diag-final...

        cmd = [fast_align_atool, '-c', 'grow-diag-final-and', '-i', forward_f.name, '-j', reverse_f.name]
        c = ProcessCommunicator(cmd, stdout_func=parse_alignments)
        c.wait()

    # -------------------------------------------
    # 4) Delete all the files...
    unlink(forward_f.name)
    unlink(reverse_f.name)
    unlink(sents_f.name)

    a_sents = AlignedCorpus()
    # print(sents_f.name)
    for e_snt, f_snt, aln in zip(e_list, f_list, alignments):
        a = AlignedSent(e_snt, f_snt, aln)
        a_sents.append(a)

    return a_sents



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
                  Alignment({(3, 2), (5, 5), (6, 6), (4, 4), (4, 3), (2, 2), (1, 1)}),
                  Alignment({(5, 5), (3, 3), (6, 6), (4, 4), (2, 2), (1, 1)})]

        self.assertEqual(aln, my_aln)
