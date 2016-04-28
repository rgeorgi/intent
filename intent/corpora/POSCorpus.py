"""
Created on Mar 6, 2014

@author: rgeorgi
"""
import os, codecs, re

import collections

from intent.utils.token import tokenize_string, tag_tokenizer, POSToken


class POSCorpusInstance(list):
    def __init__(self, seq=[], id_ref=None):
        self.id_ref = id_ref
        list.__init__(self, seq)

    def matches(self, other):
        if not isinstance(other, POSCorpusInstance):
            raise POSCorpusException('Attempting to compare non-POSCorpusInstance to POSCorpusInstance')
        if len(self) != len(other):
            raise POSCorpusException('Mismatched length in POSCorpus compare')

        zipped = zip(self, other)

        count = 0

        for my_token, o_token in zipped:
            if my_token.label == o_token.label:
                count+=1
        return count

    def append(self, token):
        if not isinstance(token, POSToken):
            raise POSCorpusException('Attempting to add non-token to POSCorpusInstance')
        else:
            if not token.index: token.index = len(self)+1
            list.append(self, token)


    def __str__(self):
        return '<POSCorpusInstance: %s>' % self.slashtags()

    def raw(self, lowercase=True):
        ret_str = ''
        for token in self:
            form = token.get_content()
            if lowercase:
                form = form.lower()
            ret_str += form+' '
        return ret_str.strip()

    def slashtags(self, delimeter = '/', lowercase=True):
        ret_str = ''
        for token in self:
            form = token.seq
            if lowercase:
                form = token.seq.lower()
            ret_str += '%s/%s ' % (form, token.label)
        return ret_str.strip()


    def mallet(self, lowercase=True):
        ret_str = ''
        for token in self:
            form = token.form
            if lowercase:
                form = token.form.lower()
            ret_str += '%s %s\n' % (form, token.label)
        return ret_str


class POSCorpus(list):
    """
    POS Tag corpus object to attempt to unify inputs and outputs.
    """

    def __init__(self, seq = None):
        if seq is None:
            seq = []
        super().__init__(seq)

    def add(self, inst):
        if not isinstance(inst, POSCorpusInstance):
            raise POSCorpusException('Attempt to add non-POSCorpusInstance to POSCorpus')
        else:
            list.append(self, inst)

    def slashtags(self, delimeter = '/', lowercase=True):
        """
        Return the corpus in slashtags ( John/NN Stewart/NN ) format.

        @param delimeter:
        @param lowercase:
        """
        ret_str = ''
        for inst in self:
            ret_str += inst.slashtags(delimeter=delimeter, lowercase=lowercase)+'\n'
        return ret_str

    def raw(self):
        ret_str = ''
        for inst in self:
            ret_str += inst.raw()+'\n'
        return ret_str

    def matches(self, other):
        if not isinstance(other, POSCorpus):
            raise POSCorpusException('Attempting to compare non-POSCorpus with POSCorpus')
        if len(self) != len(other):
            raise POSCorpusException('Attempt to compare POSCorpus instances of different length')

        zipped = zip(self, other)
        matches = 0
        for myself, other in zipped:
            matches += myself.matches(other)
        return matches

    def tokens(self):
        tokens = []
        for inst in self:
            tokens.extend(inst)
        return tokens

    def types(self):
        types = set([])
        for inst in self:
            for token in inst:
                types |= set([token.seq])
        return types

    def accuracy(self, other):
        return self.matches(other) / float(len(self.tokens()))

    def mallet(self, lowercase=True):
        ret_str = ''
        for inst in self:
            ret_str += inst.mallet(lowercase=lowercase)+'\n'
        return ret_str

    def split(self, percent = 100.):
        index = int(round((percent/100.)*len(self)))
        train = POSCorpus(self[:index])
        test = POSCorpus(self[index:])
        return train, test

    def write(self, path, format, delimeter = '/', outdir = os.getcwd(), lowercase = True):

        path = os.path.join(outdir, path)

        if path and len(self):
            f = codecs.open(path, 'w', encoding='utf-8')
            if format == 'mallet':
                f.write(self.mallet(lowercase=lowercase))
            elif format == 'slashtags':
                f.write(self.slashtags(delimeter=delimeter, lowercase=lowercase))
            elif format == 'raw':
                f.write(self.raw())
            else:
                raise POSCorpusException('Unknown output format requested.')
            f.close()

    def writesplit(self, train_path, test_path, split, format, delimeter = '/', outdir = os.getcwd(), lowercase=True):
        train, test = self.split(split)
        if train_path and len(train):
            train.write(train_path, format, delimeter, outdir, lowercase)
        if test_path and len(test):
            test.write(test_path, format, delimeter, outdir, lowercase)

    @classmethod
    def read_slashtags(cls, path, **kwargs):
        """
        Method to read in a corpus in the form of Token/TAG. (Assumes the default delimiter "/")

        :param path: File path to the slashtagged file to read in.
        :type path: str
        :param delimiter: Delimiter between token and Tag
        :type delimiter: str

        :returns: POSCorpus

        """
        delimeter = kwargs.get('delimeter', '/')

        c = cls()

        # This is the function we will use to process
        # the tokens for this instance.
        def func(tokens):
            inst = c.token_handler(tokens)
            if inst:
                c.append(inst)

        process_slashtag_file(path, func, delimeter)

        return c
            

    @classmethod
    def read_simpletagger(cls, fp, **kwargs):
        """
        Simpletagger format is used by Mallet and consists
        of one token per line, with its features listed first
        and then its label listed last.

        :param cls:
        :param fp:
        """
        f = open(fp, 'r', encoding='utf-8')
        data = f.read()
        f.close()

        # Get all the sents from the simpletagger file.
        sents = re.findall('[\s\S]+?\n\n', data)

        c = cls()

        for sent in sents:
            lines = sent.strip().split('\n')
            postokens = []
            for line in lines:
                tokens = line.split()
                label = tokens[-1]

                # With the convention used in this code,
                # a word in ST format will have a feature:
                # word-_____
                form_re = re.search('word-(\S+)', line)
                if form_re:
                    form = form_re.group(1)
                else:
                    form = '**NONE**'

                pt = POSToken(form, label=label)
                postokens.append(pt)
            inst = c.token_handler(postokens)
            if inst:
                c.append(inst)
        return c


    def token_handler(self, tokens):
        inst = POSCorpusInstance()
        for token in tokens:
            inst.append(token)
        return inst




# =============================================================================
# Universal POS Tag Tools
# =============================================================================

def process_slashtag_file(path, token_func, delimeter ='/'):
    """
    A universal function to process "slashtag"-style (e.g. Fountain/NOUN) files.

    :param path: Path to the slashtag file.
    :param func: Function to apply to each token.
    """

    # Start by opening the file.
    f = open(path, 'r', encoding='utf-8')

    tokens = 0
    lines = 0

    for line in f:
        split_tokens = tokenize_string(line, lambda x: tag_tokenizer(x, delimeter=delimeter))
        token_func(split_tokens)
        tokens += len(split_tokens)
        lines += 1

    f.close()
    return tokens, lines



def process_wsj_file(fp, token_func):
    """
    A function for processing WSJ parse files.

    :param fp:
    :type fp: str
    :param token_func:
    :return:
    """
    f = open(fp, 'r', encoding='utf-8')

    token_count = 0
    line_count = 0

    # Keep track of the open parens so we know when we have a full tree to parse.
    open_parens = 0

    cur_tree = ''
    for line in f:

        # Skip blank lines
        if not line.strip():
            continue

        # Count the number of open parens.
        open_parens += len(re.findall('\(', line))
        open_parens -= len(re.findall('\)', line))

        cur_tree += line.strip() + ' '

        # If the running count of open parens
        # matches the count of closed parens,
        # we should have a complete tree.
        if open_parens == 0:
            # Parse the tree...
            from intent.trees import IdTree
            t = IdTree.fromstring(cur_tree, remove_empty_top_bracketing=True)

            # Now, process the tokens...
            tokens = t.tagged_words()
            token_func(tokens)

            # Increment the counts
            token_count += len(tokens)
            line_count += 1

            # And reset the tree string.
            cur_tree = ''

    return token_count, line_count

# =============================================================================

class POSCorpusException(Exception):
    def __init__(self, msg = None):
        Exception.__init__(self, msg)


