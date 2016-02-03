'''
Created on Jan 31, 2014

@author: rgeorgi
'''
import sys

from intent.interfaces.stanford_tagger import StanfordPOSTagger
from intent.utils.env import tagger_model
import collections

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
        self.form = self.form.lower()
        self.lemma = self.lemma.lower()

    def apply_func(self, func):
        self.form = func(self.form)
        self.lemma = func(self.lemma)

class ConllSentence(list):
    def __str__(self):
        ret_str = ''
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

    def __iter__(self) -> ConllWord:
        return super().__iter__()

    def lower(self):
        for word in self:
            word.lower()

    def apply_func(self):
        for word in self:
            word.apply_func()



class ConllCorpus(list):


    @classmethod
    def read(cls, path, lowercase=True):
        """
        :rtype: ConllCorpus
        """
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
                    w = ConllWord(*line.split(), lowercase=lowercase)
                    cur_sent.append(w)

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

    def __iter__(self) -> ConllSentence:
        return super().__iter__()

if __name__ == '__main__':
    cc = ConllCorpus.read(sys.argv[1])
    sp = StanfordPOSTagger('/Users/rgeorgi/Documents/code/intent/experiments/dependencies/proj-heur/sv.tagger')
    cc.tag(sp)
    print(cc)

