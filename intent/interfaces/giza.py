"""
Created on Feb 14, 2014

.. codeauthor::Ryan Georgi <rgeorgi@uw.edu>
"""

# Built-in imports -------------------------------------------------------------
import os, sys, re, glob, logging

# Internal imports -------------------------------------------------------------
import shutil
import stat
from intent.alignment.Alignment import AlignedSent,	Alignment
from intent.utils.env import c
from intent.utils.fileutils import swapext
from intent.utils.systematizing import piperunner, ProcessCommunicator

# Other imports ----------------------------------------------------------------
from tempfile import mkdtemp
from collections import defaultdict
from unittest.case import TestCase

GIZA_LOG = logging.getLogger("GIZA")


class GizaAlignmentException(Exception):
    """
    An exception class for Giza errors.
    """

class CooccurrenceFile(defaultdict):
    """
    An internal representation of a cooccurrence file.
    """
    def __init__(self):
        defaultdict.__init__(self, set)

    def dump(self, path = None):

        if not path:
            f = sys.stdout
        else:
            f = open(path, 'w', encoding='utf-8')

        for key in sorted(self.keys()):
            for entry in sorted(self[key]):
                f.write('%d %d\n' % (key, entry))

        f.flush()

class A3files(object):
    def __init__(self, prefix):
        self.files = glob.glob(prefix+'.A3.final.part*')
        self.prefix = prefix

    def merge(self, merged_path):

        sentdict = {}

        for filename in self.files:
            f = open(filename, 'r', encoding='utf-8')
            lines = f.readlines()
            f.close()

            while lines:
                line1 = lines.pop(0)
                line2 = lines.pop(0)
                line3 = lines.pop(0)

                num = int(re.search('pair \(([0-9]+)\)', line1).group(1))
                sentdict[num] = (line1,line2,line3)

        # Create and write out the merged file
        merged_f = open(merged_path, 'w', encoding='utf-8')
        for key in sorted(sentdict.keys()):
            for line in sentdict[key]:
                merged_f.write(line)

        merged_f.close()




class GizaFiles(object):
    """
    Giza produces so many files, it's easy just to initialize an object to represent
    all the files that will be produced, based on the input F, E text files, and the prefix
    provided for output.
    """

    def __init__(self, prefix, e, f):
        self.e = e
        self.f = f
        self.prefix = prefix

    @property
    def cfg(self):
        return self.prefix+'.gizacfg'

    @property
    def e_vcb(self):
        return swapext(self.e, '.vcb')

    @property
    def f_vcb(self):
        return swapext(self.f, '.vcb')

    @property
    def ef(self):
        return os.path.splitext(self.e)[0]+'_'+os.path.basename(os.path.splitext(self.f)[0])

    @property
    def fe(self):
        return os.path.splitext(self.f)[0]+'_'+os.path.basename(os.path.splitext(self.e)[0])

    @property
    def ef_snt(self):
        return self.ef+'.snt'

    @property
    def fe_snt(self):
        return self.fe+'.snt'

    @property
    def ef_cooc(self):
        return self.ef+'.cooc'

    @property
    def fe_cooc(self):
        return self.fe+'.cooc'

    @property
    def a3(self):
        return glob.glob(self.prefix+'.A3.final.part*')

    @property
    def a3merged(self):
        return self.prefix+'.A3.final.merged'

    @property
    def t(self):
        return self.prefix+'.t3.final'

    @property
    def a(self):
        return self.prefix+'.a3.final'

    @property
    def n(self):
        return self.prefix+'.n3.final'

    @property
    def d3(self):
        return self.prefix+'.d3.final'

    @property
    def d4(self):
        return self.prefix+'.d4.final'

    @property
    def perp(self):
        return self.prefix+'.perp'

    @property
    def p0(self):
        return self.prefix+'.p0_3.final'

    @property
    def decoder(self):
        return self.prefix+'.Decoder.config'

    def _clean(self, ls):
        for f in ls:
            try:
                os.remove(f)
            except:
                pass

    def merge_a3(self):
        GIZA_LOG.debug("Merging A3 files in {}".format(self.prefix))
        a3 = A3files(self.prefix)
        a3.merge(self.a3merged)

    def clean(self):
        GIZA_LOG.debug("Removing unnecessary files...")
        self.merge_a3()

        filelist = [self.ef_cooc, self.fe_cooc,
                    self.t, self.d3, self.d4, self.n, self.a,
                    self.e_vcb, self.f_vcb,
                    self.ef_snt, self.fe_snt,
                    self.cfg, self.perp, self.p0, self.decoder]


        filelist.extend(self.a3)
        filelist.extend(glob.glob(self.prefix+'.trn*'))
        filelist.extend(glob.glob(self.prefix+'.tst*'))


        self._clean(filelist)



    def txt_to_snt(self, ev = None, fv = None):
        """
        This function will generate .snt files in the appropriate place based
        on the vocabularies and text files provided.
        """

        # --- 1) If we are provided with Vocab objects,
        #        use those. Otherwise, attempt to load the files.
        #        finally, attempt to create new ones.
        if not ev:
            if os.path.exists(self.e_vcb):
                ev = Vocab.load(self.e_vcb)
            else:
                ev = Vocab()


        if not fv:
            if os.path.exists(self.f_vcb):
                fv = Vocab.load(self.f_vcb)
            else:
                fv = Vocab()

        # --- 2) Load the text files.
        ef = open(self.e, encoding='utf-8')
        ff = open(self.f, encoding='utf-8')

        ef_lines = ef.readlines()
        ff_lines = ff.readlines()

        # --- 3) Verify the files are the same length
        if len(ef_lines) != len(ff_lines):
            raise GizaAlignmentException('Files are of unequal length. %d vs. %d' % (len(ef_lines), len(ff_lines)))

        # --- 4) Attempt to open up the snt file locations for writing...
        ef_file = open(self.ef_snt, 'w', encoding='utf-8')
        fe_file = open(self.fe_snt, 'w', encoding='utf-8')

        # --- 5) While we are at it, let's make the cooc files.
        ef_cooc = CooccurrenceFile()
        fe_cooc = CooccurrenceFile()

        # --- 4) Otherwise, proceed converting text files with the vocab...
        for e_line, f_line in zip(ef_lines, ff_lines):

            # Skip if one of the lines is empty...
            if (not e_line.strip()) or (not f_line.strip()):
                continue

            e_snt_ids = ev.string_to_ids(e_line, add=True)
            f_snt_ids = fv.string_to_ids(f_line, add=True)

            e_snt = ev.string_to_snt(e_line)
            f_snt = fv.string_to_snt(f_line)

            # The cooc file contains every id
            # for '0', and then, for every e_id,
            # the f_ids that it is seen co-ocurring with.
            #
            # So, let's build that database.
            for e_id in e_snt_ids:
                fe_cooc[0].add(e_id)

                for f_id in f_snt_ids:
                    ef_cooc[e_id].add(f_id)


            for f_id in f_snt_ids:
                ef_cooc[0].add(f_id)

                for e_id in e_snt_ids:
                    fe_cooc[f_id].add(e_id)


            # Write the special "1" token to each file
            ef_file.write('1\n')
            ef_file.write('%s\n%s\n' % (e_snt, f_snt))

            fe_file.write('1\n')
            fe_file.write('%s\n%s\n' % (f_snt, e_snt))

            ef_file.flush(), fe_file.flush()

        # --- 5) Dump our (posisbly) updated vocab files
        ev.dump(self.e_vcb)
        fv.dump(self.f_vcb)

        # --- 6) Also dump our coocurrence files...
        ef_cooc.dump(self.ef_cooc)
        fe_cooc.dump(self.fe_cooc)



    # Read the aligned file here...
    def aligned_sents(self):
        """
        Read in the (merged) A3 file and return the AlignedSents of (src, tgt) alignments.

        :rtype: list of :py:class:`~alignment.AlignedSent` instances
        """
        a_f = open(self.a3merged, 'r', encoding='utf-8')
        lines = a_f.readlines()
        a_f.close()

        a_sents = []

        while lines:
            top = lines.pop(0)
            tgt = lines.pop(0)
            aln = lines.pop(0)

            a_sents.append(AlignedSent.from_giza_lines(tgt, aln))


        return a_sents


class VocabWord(object):
    """
    A simple class to contain words in the vocab and keep track of their ID, while hashing the same as the string that they represent.
    """
    def __init__(self, word, id):
        """
        :param word: string that the word represents
        :type word: str
        :param id: Integer ID to identify the string by
        :type id: int
        """
        self.id = id
        self.content = word

    def __hash__(self):
        return hash(self.content)

    def __eq__(self, o):
        return str(self) == str(o)

    def __str__(self):
        return self.content

    def __repr__(self):
        return '%s[%s]' % (self.content, self.id)

class VocabNotFoundException(Exception):
    pass

class Vocab(object):
    """
    Internal representation for a .vcb file, so that they can be quickly rewritten.

    Note that "1" is the symbol reserved for end-of-sentence, so the indices should start with "2"
    """

    def __init__(self):
        self._counts = {}
        self._words = {}
        self._i = 1

    def __len__(self):
        return self._i

    def add(self, word, count=1):
        """
        Add a word to the vocab and assign it a new id.
        """
        if word in self._counts:
            self._counts[word] += count
            return self._words[word].id
        else:
            self._i += 1
            vw = VocabWord(word, self._i)
            self._counts[vw] = count
            self._words[vw] = vw
            return self._i

    def add_from_txt(self, path):
        f = open(path, 'r', encoding='utf-8')
        lines = f.readlines()
        f.close()
        for line in lines:
            for word in line.split():
                self.add(word)

    def get_id(self, w, add=False):
        """
        Get the ID for a word. If "add" is False, raise an exception if the word
        is not found in the vocab. Otherwise, add it and return the new ID.
        """
        if self._words.get(w):
            if add:
                return self.add(w)
            else:
                return self._words.get(w).id
        elif not add:
            raise VocabNotFoundException
        else:
            return self.add(w)

    def string_to_ids(self, string, add=False):
        """
        Given a string, convert it to the ids representation expected by GIZA, using the words
        in this vocab. If an unknown word is discovered, raise an Exception.
        """

        words = string.split()

        ids = [self.get_id(w, add) for w in words]
        return ids

    def string_to_snt(self, string, add=False):
        """
        Do what string_to_ids does, but return a string.
        """
        return ' '.join([str(i) for i in self.string_to_ids(string, add)])




    @classmethod
    def load(cls, path):
        """
        Create a vocab object from a path.

        :param path: Path to the .vcb file to load
        :type path: filepath
        """
        v = cls()
        f = open(path, 'r', encoding='utf-8')
        lines = f.readlines()
        f.close()

        # Each line looks like this:
        #
        # ID  WORD COUNT
        # 163 top 650

        for line in lines:
            id, word, count =  line.split()
            v.add(word, int(count))

        return v


    def items(self):
        return sorted(self._counts.items(), key=lambda i: i[0].id)

    def dump(self, path=None):
        if not path:
            fh = sys.stdout
        else:
            fh = open(path, 'w', encoding='utf-8')

        for vw, count in self.items():
            fh.write('%s %s %s\n' % (vw.id, vw.content, count))
        fh.flush()


class GizaAligner(object):
    """
    A class to run GIZA
    """

    def train(self, prefix, e, f):
        """
        Train the giza word alignments on the provided text files.

        :param prefix: Prefix for where the giza output files will be stored.
        :type prefix: path+prefix
        :param e: Path to the "e" file
        :type e: path
        :param f: Path to the "f"
        :type f: path
        """
        self.tf = GizaFiles(prefix, e, f)
        tf = self.tf

        self.tf.txt_to_snt(ev = Vocab(), fv = Vocab())

        # Now, do the aligning...
        exe = c.getpath('mgiza')

        if exe is None:
            raise GizaAlignmentException('Path to mgiza binary not defined.')
        elif not os.path.exists(exe):
            raise GizaAlignmentException('Path to mgiza binary "%s" invalid.')


        elts = [exe,
                '-o', tf.prefix,
                '-S', tf.e_vcb,
                '-T', tf.f_vcb,
                '-C', tf.ef_snt,
                '-CoocurrenceFile', tf.ef_cooc,
                '-hmmiterations', '5',
                '-model4iterations', '0',
                '-ncpus', '0']
        cmd = ' '.join(elts)

        GIZA_LOG.debug('Command: "{}"'.format(cmd))

        p = ProcessCommunicator(elts)
        status = p.wait()
        GIZA_LOG.debug("Exit code: {}".format(str(status)))

        if status != 0:
            raise GizaAlignmentException("mgiza exited abnormally with a return code of {}".format(str(status)))

        tf.merge_a3()
        # tf.clean()

        return tf.aligned_sents()

    def force_align(self, e_snts, f_snts):
        return self.temp_align(e_snts, f_snts, self.resume)

    def temp_train(self, e_snts, f_snts):
        return self.temp_align(e_snts, f_snts, self.train)

    def temp_align(self, e_snts, f_snts, func):
        """

        :param e_snts: e sentences
        :type e_snts: [str]
        :param f_snts: f sentences
        :type f_snts: [str]
        :param func: The function to use on the data, either training from scratch or resuming.
        :type func: method
        """
        tempdir = mkdtemp()
        # tempdir = '/tmp/tmp3pnlk0oi'

        # Set the temp dir to world-readable... (for debugging)
        # os.chmod(tempdir, stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        #          | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        g_path = os.path.join(tempdir, 'g.txt')
        t_path = os.path.join(tempdir, 't.txt')

        g_f = open(g_path, 'w', encoding='utf-8')
        t_f = open(t_path, 'w', encoding='utf-8')

        for snt in e_snts:
            g_f.write(snt+'\n')
        for snt in f_snts:
            t_f.write(snt+'\n')

        g_f.close(), t_f.close()

        prefix = os.path.join(tempdir, 'temp')

        aln = func(prefix, g_path, t_path)
        shutil.rmtree(tempdir)
        return aln


    def resume(self, prefix, new_e, new_f):
        """
        "Force" align a new set of data using the old
        model, per the instructions at:

        http://www.kyloo.net/software/doku.php/mgiza:forcealignment

        """
        # First, initialize a new GizaFile container for
        # the files we are going to create

        new_gf = GizaFiles(prefix, new_e, new_f)

        # Now, we're going to extend the old vocabulary files
        # with the new text to align.
        old_ev = Vocab.load(self.tf.e_vcb)
        old_fv = Vocab.load(self.tf.f_vcb)

        old_ev.add_from_txt(new_gf.e)
        old_fv.add_from_txt(new_gf.f)

        # Now that we've extended the vocabs, let's dump the
        # now-extended vocabs into the new filepaths.
        old_ev.dump(new_gf.e_vcb)
        old_fv.dump(new_gf.f_vcb)

        # Write out
        new_gf.txt_to_snt(ev = old_ev, fv = old_fv)

        exe = c.getpath('mgiza')

        if exe is None:
            raise GizaAlignmentException('Path to mgiza binary not defined.')
        elif not os.path.exists(exe):
            raise GizaAlignmentException('Path to mgiza binary "%s" invalid.' % exe)

        args = [exe, #self.tf.cfg,
                '-restart', '2',
                '-o', new_gf.prefix,
                '-m2', '5',
                '-previoust', self.tf.t,
                '-previousa', self.tf.a,
                '-previousn', self.tf.n,
                '-previousd', self.tf.d3,
                '-c', new_gf.ef_snt,
                '-s', new_gf.e_vcb,
                '-t', new_gf.f_vcb,
                '-Coocurrencefile', new_gf.ef_cooc]

        cmd = ' '.join(args)
        GIZA_LOG.debug('Command: "{}"'.format(cmd))

        p = ProcessCommunicator(args)
        status = p.wait()

        GIZA_LOG.debug("Exit status {}".format(str(status)))

        if status != 0:
            raise GizaAlignmentException("mgiza exited abnormally with a return code of {}".format(str(status)))



        new_gf.merge_a3()
        # new_gf.clean()

        return new_gf.aligned_sents()



    @classmethod
    def load(cls, prefix, e, f):
        """
        Load a stored giza alignment file to resume

        :param prefix: Prefix for the non-text files
        :type prefix: path+base
        :param e: Path to the "e" file
        :type e: path
        :param f: Path to the "f" file
        :type f: path
        """
        ga = cls()
        ga.tf = GizaFiles(prefix, e, f)
        return ga

        # After training, return the aligned sentences:

# 	intersected = combine_corpora(g_t_giza_ac, t_g_giza_ac, method='intersect')
# 	union = combine_corpora(g_t_giza_ac, t_g_giza_ac, method='union')
# 	refined = combine_corpora(g_t_giza_ac, t_g_giza_ac, method='refined')
# 	
# 	g_t_ae = AlignEval(g_t_giza_ac, gold_ac, debug=False)
# 	t_g_ae = AlignEval(t_g_giza_ac, gold_ac, debug=False, reverse=True)
# 	i_ae = AlignEval(intersected, gold_ac, debug=False)
# 	union_ae = AlignEval(union, gold_ac, debug=False)
# 	refined_ae = AlignEval(refined, gold_ac, debug=False)
# 	
# 	print('System,AER,Precision,Recall,F-Measure,Matches,Gold,Test')
# 	print(r'Gloss $\rightarrow$ Trans,%s'%g_t_ae.all())
# 	print(r'Trans $\rightarrow$ Gloss,%s'%t_g_ae.all())
# 	print(r'Intersection,%s'%i_ae.all())
# 	print(r'Union,%s'%union_ae.all())
# 	print(r'Refined,%s'%refined_ae.all())


#===============================================================================
# Unit Tests
#===============================================================================

class TestTrain(TestCase):

    def test_giza_train_toy(self):
        ga = GizaAligner()

        e_snts = ['the house is blue',
                   'my dog is in the house',
                   'the house is big',
                   'house']

        f_snts = ['das haus ist blau',
                    'meine hund ist in dem haus',
                    'das haus ist gross',
                    'haus']

        a_snts = ga.temp_train(e_snts, f_snts)
        self.assertEqual(a_snts[0].aln, Alignment([(1,1),(2,2),(3,3),(4,4)]))
