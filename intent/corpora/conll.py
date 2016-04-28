'''
Created on Jan 31, 2014

@author: rgeorgi
'''
import sys

from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.pos.TagMap import TagMap

from intent.utils.dicts import CountDict, TwoLevelCountDict

"""
Field number: 	Field name: 	Description:
1 	ID 	Token counter, starting at 1 for each new sentence.
2 	FORM 	Word form or punctuation symbol.
3 	LEMMA 	Lemma or stem (depending on particular data set) of word form, or an underscore if not available.
4 	CPOSTAG 	Coarse-grained part-of-speech tag, where tagset depends on the language.
5 	POSTAG 	Fine-grained part-of-speech tag, where the tagset depends on the language,
            or identical to the coarse-grained part-of-speech tag if not available.
6 	FEATS 	Unordered set of syntactic and/or morphological features (depending on the particular
            language), separated by a vertical bar (|), or an underscore if not available.
7 	HEAD 	Head of the current token, which is either a value of ID or zero ('0').
            Note that depending on the original treebank annotation, there may be
            multiple tokens with an ID of zero.
8 	DEPREL 	Dependency relation to the HEAD. The set of dependency relations depends on the particular language.
            Note that depending on the original treebank annotation, the dependency relation may be meaningfull
            or simply 'ROOT'.
9 	PHEAD 	Projective head of current token, which is either a value of ID or
            zero ('0'), or an underscore if not available. Note that depending
            on the original treebank annotation, there may be multiple tokens an
            with ID of zero. The dependency structure resulting from the PHEAD column is
            guaranteed to be projective (but is not available for all languages), whereas the structures
            resulting from the HEAD column will be non-projective for some sentences of some languages
            (but is always available).
10 	PDEPREL 	Dependency relation to the PHEAD, or an underscore if not available. The set of dependency
                relations depends on the particular language. Note that depending on the original
                treebank annotation, the dependency relation may be meaningfull or simply 'ROOT'.
"""

def _u(s):
    if s == '_':
        return None
    else:
        return s

def _s(f):
    if f is None:
        return '_'
    else:
        return str(f)

class ConllWord(object):
    def __init__(self, id=None, form=None, lemma=None, cpostag=None, postag=None, feats=None, head=None, deprel=None, phead=None, pdeprel=None):
        self.id = id
        self.form    = _u(form)
        self.lemma   = _u(lemma)
        self.cpostag = _u(cpostag)
        self.postag  = _u(postag)
        self.feats   = _u(feats)
        self.head    = _u(head)
        self.deprel  = _u(deprel)
        self.phead   = _u(phead)
        self.pdeprel = _u(pdeprel)

    def __str__(self):
        ret_str = str(self.id)+'\t{}'*9
        ret_str = ret_str.format(_s(self.form),
                                 _s(self.lemma),
                                 _s(self.cpostag),
                                 _s(self.postag),
                                 _s(self.feats),
                                 _s(self.head),
                                 _s(self.deprel),
                                 _s(self.phead),
                                 _s(self.pdeprel))
        return ret_str



    def slashtags(self, delimiter='/'):
        return '{}{}{}'.format(self.form, delimiter, self.cpostag)

    def lower(self):
        self.form  = self.form.lower()  if self.form  is not None else None
        self.lemma = self.lemma.lower() if self.lemma is not None else None

    def apply_func(self, func):
        self.form = func(self.form)
        self.lemma = func(self.lemma)

class ConllSentence(list):
    def __str__(self):
        return '\n'.join([str(i) for i in self])

    def slashtags(self, delimiter='/'):
        return ' '.join([i.slashtags(delimiter) for i in self])

    def raw(self):
        return ' '.join([i.form for i in self])

    def __getitem__(self, item) -> ConllWord:
        return super().__getitem__(item)

    def tag(self, tagger: StanfordPOSTagger = None):
        """
        Tag the given sentence.
        """
        tags = tagger.tag(self.raw())
        for i, tag in enumerate(tags):
            self[i].cpostag = tag.label
            self[i].postag  = tag.label

    def __iter__(self):
        """
        :rtype: collections.Iterable[ConllWord]
        """
        return super().__iter__()

    def lower(self):
        for word in self:
            word.lower()

    def apply_func(self):
        for word in self:
            word.apply_func()

    def strip_tags(self):
        for word in self:
            word.cpostag = None
            word.postag = None

    def strip_feats(self):
        for word in self:
            word.feats = None


class ConllCorpus(list):


    @classmethod
    def read(cls, path, lowercase=False, tagmap=None):
        """
        :rtype: ConllCorpus
        """
        if tagmap is not None:
            tm = TagMap(tagmap)

        with open(path, 'r', encoding='utf-8') as f:
            corp = cls()

            cur_sent = None
            for line in f:
                if not line.strip():
                    if cur_sent is not None:
                        corp.append(cur_sent)
                        cur_sent = None
                    continue

                else:
                    if cur_sent is None:
                        cur_sent = ConllSentence()
                    w = ConllWord(*line.split())

                    # Lowercase the word if requested (and its lemma)
                    if lowercase:
                        w.lower()

                    # Remap the tags if a tagmap is provided.
                    if tagmap is not None:
                        w.cpostag = tm[w.cpostag] if w.cpostag else None

                    cur_sent.append(w)

            # If the end of the file is reached without a blank line,
            # Make sure to still add the last sentence.
            if line.strip():
                corp.append(cur_sent)
        return corp

    def raw(self):
        return '\n'.join([i.raw() for i in self])

    def __str__(self):
        return '\n\n'.join([str(i) for i in self])

    def slashtags(self, delimiter='/'):
        """
        Produce a slashtags corpus.
        """
        return '\n'.join([i.slashtags(delimiter) for i in self])

    def tag(self, tagger):
        """
        Use the provided tagger to write POS tags to the file.
        """
        for s in self:
            s.tag(tagger)

    def write(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(self))

    def __iter__(self):
        """
        :rtype: collections.Iterable[ConllSentence]
        """
        return super().__iter__()

    def lower(self):
        for sent in self:
            sent.lower()

    def strip_tags(self):
        """
        Remove the POS tag information from the sentences.
        """
        for sent in self:
            sent.strip_tags()

    def strip_feats(self):
        """
        Remove the features from the sentences.
        """
        for sent in self:
            sent.strip_feats()

    def prune_to_token_length(self, max_tokens):
        new_cc = ConllCorpus()
        total_tokens = 0
        for sent in self:
            total_tokens += len(sent)
            new_cc.append(sent)
            if total_tokens >= max_tokens:
                break
        return new_cc

# =============================================================================
# EVALUATION
# =============================================================================



class ConllEval(object):
    def __init__(self):
        self.dep_acc_by_pos = TwoLevelCountDict()
        self.head_acc_by_pos = TwoLevelCountDict()

        self.long_sent_stats = CountDict()
        self.short_sent_stats = CountDict()

        self.fields = ['pos_acc', 'ul_acc', 'l_acc']

    def add(self, k, sent):
        self.long_sent_stats.add(k)
        if len(sent) < 10:
            self.short_sent_stats.add(k)

    def pos_stats(self):

        for pos in sorted(set(self.dep_acc_by_pos.keys()).union(set(self.head_acc_by_pos.keys()))):
            print(','.join([pos, str(self.dep_acc_by_pos.sub_distribution(pos).get(True, 0.)), str(self.head_acc_by_pos.sub_distribution(pos).get(True, 0.))]))

    def acc(self, d, k):
        return d[k]/d['words']*100

    def long_stats(self):
        return [self.acc(self.long_sent_stats, k) for k in self.fields]

    def short_stats(self):
        return [self.acc(self.short_sent_stats, k) for k in self.fields]

    def short_ul(self):
        return self.acc(self.short_sent_stats, 'ul_acc')

    def short_ul_count(self):
        return self.short_sent_stats.get('ul_acc', 0)

    def short_words(self):
        return self.short_sent_stats.get('words', 0)

    def long_ul(self):
        return self.acc(self.long_sent_stats, 'ul_acc')

    def long_ul_count(self):
        return self.long_sent_stats.get('ul_acc', 0)

    def long_words(self):
        return self.long_sent_stats.get('words', 0)


def eval_conll_paths(gold_path, target_path) -> ConllEval:
    """
    Given the paths to a gold file and target file, parse them
    and then evaluate
    """
    g = ConllCorpus.read(gold_path)
    t = ConllCorpus.read(target_path)

    assert len(g) == len(t)
    return eval_conll(g, t)

def eval_conll(gold: ConllCorpus, target: ConllCorpus, out_stream = sys.stdout, pos_breakdown=False) -> ConllEval:

    # -------------------------------------------
    # Gather statistics
    # -------------------------------------------
    ce = ConllEval()

    # -------------------------------------------

    assert len(gold) == len(target)
    for goldsent, targetsent in zip(gold, target):

        assert len(goldsent) == len(targetsent)
        for goldword, targetword in zip(goldsent, targetsent):

            assert isinstance(goldword, ConllWord)
            assert isinstance(targetword, ConllWord)

            def add_stat(k):
                ce.add(k, goldsent)

            # -------------------------------------------
            # Enter the childpos-parentpos pair in the matrix
            # -------------------------------------------
            # TODO: FIXME: Lazy fix for "." vs. "PUNC"
            def getpos(w):
                if w.cpostag in ['.','PUNC']:
                    return 'PUNC'
                else:
                    return w.cpostag

            def getparentpos(w, sent):
                if w.head and int(w.head) > 0:
                    return getpos(sent[int(w.head)-1])
                else:
                    return 'ROOT'


            # Do the pos tags match?
            if getpos(goldword) == getpos(targetword):
                add_stat('pos_acc')

            # Do the dependency types match
            if goldword.head == targetword.head:
                add_stat('ul_acc')

                golddep = None if goldword.deprel is None else goldword.deprel.lower()
                tgtdep  = None if targetword.deprel is None else targetword.deprel.lower()
                if golddep == tgtdep:
                    add_stat('l_acc')


                ce.dep_acc_by_pos.add(getpos(targetword), True)
                ce.head_acc_by_pos.add(getparentpos(targetword, targetsent), True)
            else:
                ce.dep_acc_by_pos.add(getpos(targetword), False)
                ce.head_acc_by_pos.add(getparentpos(targetword, targetsent), False)

            add_stat('words')

    return ce


if __name__ == '__main__':
    eval_conll_paths('/Users/rgeorgi/Documents/treebanks/universal_treebanks_v2.0/std/de/punctest.conll',
                     '/Users/rgeorgi/Documents/code/intent/experiments/dependencies/proj-heurpos/deu_class_out_tagged.txt')

