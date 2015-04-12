"""
Created on Mar 21, 2014

@author: rgeorgi
"""
from intent.utils.string_utils import string_compare_with_processing
import re

# ===============================================================================
# Main Token Class
#===============================================================================

class Token(object):
    def __init__(self, content, **kwargs):

        self.content = content
        self.start = kwargs.get('start')
        self.stop = kwargs.get('stop')
        self.index = kwargs.get('index')
        self.attributes = {}
        self._parent = kwargs.get('parent')


    def __str__(self):
        return self.content

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.content)

    @property
    def parent(self):
        return self._parent

    def lower(self):
        return str(self).lower()

    @parent.setter
    def parent(self, v):
        self._parent = v

    @property
    def attrs(self):
        return self.attributes

    @attrs.getter
    def attrs(self):
        return self.attributes

    @property
    def seq(self):
        return self.content

    def value(self):
        return self.content

    def __eq__(self, o):
        return str(self) == str(o)

    def morphs(self, **kwargs):
        for morph in self.morphed_tokens():
            if kwargs.get('lowercase'):
                morph = Morph(morph.seq.lower(), morph.span, morph.parent)
            yield morph


    def morphed_tokens(self):
        morphs = list(tokenize_string(self.seq, morpheme_tokenizer))

        # If the tokenization yields no tokens, just return the string.
        if self.seq and len(morphs) == 0:
            yield Morph(self.seq, parent=self)

        for morph in morphs:
            yield (Morph.fromToken(morph, parent=self))

    def morphequals(self, o, **kwargs):
        return string_compare_with_processing(self.seq, o.seq, **kwargs)


#===============================================================================
# POSToken
#===============================================================================

class POSToken(Token):
    def __init__(self, content, **kwargs):
        Token.__init__(self, content, **kwargs)
        if 'label' in kwargs:
            self.label = kwargs.get('label')


    def __str__(self):
        return '<%s %s [%s]>' % (self.__class__.__name__, self.content, self.label)

    @property
    def label(self):
        return self.attributes.get('label')

    @label.setter
    def label(self, v):
        if v:
            self.attributes['label'] = v


    @classmethod
    def fromToken(cls, t, **kwargs):
        return cls(t.seq, **kwargs)


class GoldTagPOSToken(Token):
    def __init__(self, content, **kwargs):
        Token.__init__(self, content, **kwargs)
        self.taglabel = kwargs.get('taglabel')
        self.goldlabel = kwargs.get('goldlabel')

    @classmethod
    def fromToken(cls, t, taglabel=None, goldlabel=None):
        return cls(t.get_content(), taglabel=taglabel, goldlabel=goldlabel, index=t.index, start=t.start, stop=t.stop,
            parent=t._parent)

    @property
    def taglabel(self):
        return self.attributes.get('taglabel')

    @taglabel.setter
    def taglabel(self, v):
        self.attributes['taglabel'] = v

    @property
    def goldlabel(self):
        return self.attributes.get('goldlabel')

    @goldlabel.setter
    def goldlabel(self, v):
        self.attributes['goldlabel'] = v


#===============================================================================
# Morph
#===============================================================================

class Morph(Token):
    """
    This class is what makes up an IGTToken. Should be comparable to a token
    """

    def __init__(self, seq='', start=None, stop=None, parent=None):
        index = parent.index if parent else None
        Token.__init__(self, content=seq, start=start, stop=stop, index=index, parent=parent, tier=parent)


    @classmethod
    def fromToken(cls, token, parent):
        return cls(token.seq, start=token.start, stop=token.stop, parent=parent)

    def __str__(self):
        return '<Morph: %s>' % self.seq


#===============================================================================
# Tokenization Methods
#===============================================================================

def whitespace_tokenizer(st):
    i = 1
    for match in re.finditer('\S+', st, re.UNICODE):
        yield Token(match.group(0), start=match.start(), stop=match.end(), index=i)
        i += 1


def morpheme_tokenizer(st):
    """
    Tokenize a string splitting it on typical morpheme boundaries: [ - . : = ( ) ]
    :param st:
    """

    pieces = re.finditer('[^\s\-\.:/\(\)=]+', st)

    for match in pieces:
        if match.group().strip():
            yield Morph(match.group(0), start=match.start(), stop=match.end())


def tag_tokenizer(st, delimeter='/'):
    for match in re.finditer('(\S+){}(\S+)'.format(delimeter), st, re.UNICODE):
        yield POSToken(match.group(1), label=match.group(2), start=match.start(), stop=match.end())


def tokenize_item(it, tokenizer=whitespace_tokenizer):
    tokens = tokenize_string(it.get_content(), tokenizer)
    return tokens


def tokenize_string(st, tokenizer=whitespace_tokenizer):
    tokens = Tokenization()
    iter = tokenizer(st)

    i = 0
    for token in iter:
        token.index = i + 1
        tokens.append(token)
        i += 1
    return tokens


#===============================================================================
# Tokenization helper classes
#===============================================================================

class Tokenization(list):
    """
    Container class for a tokenization.
    """

    def __init__(self, seq=[], original=''):
        self.original = original
        list.__init__(self, seq)

    def text(self):
        return ' '.join([t.seq for t in self])


class Span(object):
    """
    Just return a character span.
    """

    def __init__(self, tup):
        """
        Constructor
        """
        self._start = tup[0]
        self._stop = tup[1]

    @property
    def start(self):
        return self._start

    @property
    def stop(self):
        return self._stop

    def __str__(self):
        return '(%s,%s)' % (self._start, self._stop)

    def __repr__(self):
        return str(self)


#===============================================================================
# Exceptions
#===============================================================================

class TokenException(Exception):
    pass