# coding=UTF-8
"""
Created on Mar 11, 2014

@author: rgeorgi
"""

import re
import unittest
import string

# ===============================================================================
# Sub-tasks of cleaning
# ===============================================================================
from xigt.model import Tier, Item, Igt, XigtCorpus
from xigt.codecs.xigtxml import encode_tier, encode_item, encode_igt, encode_xigtcorpus

punc_chars   = '\.,\'\"\?!\xc2'
punc_re      = '[{}]'.format(punc_chars)
punc_re_mult = '{}+'.format(punc_re)
no_punc_re   = '[^{}]'.format(punc_chars)
word_re      = '[^{}\s]+'.format(punc_chars)

list_re = '(?:[0-9]+|[a-z]|i+)'
quote_re = '[\'"\`]'


def grammaticality(ret_str):
    # Now, remove leading grammaticality markers
    return re.sub('([#\*\?]+)', replace_group_with_whitespace, ret_str)


def surrounding_quotes_and_parens(ret_str):
    ret_str = re.sub('^\s*([\'"`\[\(]+)', replace_group_with_whitespace, ret_str)
    ret_str = re.sub('([\'"`\]\)\.]+)\s*$', replace_group_with_whitespace, ret_str)
    return ret_str


def split_punctuation(ret_str):
    return re.sub(r'(\w+)([.?!,])+', r'\1 \2', ret_str).strip()


def remove_external_punctuation(ret_str):
    ret_str = re.sub(r'(\w+)({})+\s'.format(punc_chars), r'\1 ', ret_str, flags=re.U)
    ret_str = re.sub(r'(?:^|\s)({}+)(\w+)'.format(punc_chars), r'\2', ret_str, flags=re.U)
    return re.sub(r'(\w+)([{}])+$'.format(punc_chars), r'\1 ', ret_str, flags=re.U)


def join_morphs(ret_str):
    """
    Find tokens that have letters or numbers on two sides separated by a
    period or morph and join them.

    E.g. MASC . 1SG becomes "MASC.1SG"
    """
    m = re.sub('([\w\d])\s*([\.\-])\s*(?=[\w\d])', r'\1\2', ret_str)
    return m


def fix_grams(ret_str):
    """
    Search for gram strings that have been split with whitespace and rejoin them.

    For instance "3 SG" will become "3SG"
    """
    for gram in ['3SG', '1PL', '2SG', '2PL']:
        for i in range(1, len(gram) + 1):
            first, last = gram[:i], gram[i:]

            if first and last:
                expr = '%s\s+%s' % (first, last)
                ret_str = re.sub(expr, gram, ret_str, flags=re.I)
    return ret_str


def remove_elipses(ret_str):
    return re.sub('\.\s*\.\s*\.', '', ret_str)


def remove_solo_punctuation(ret_str):
    ret_str = re.sub('\s*({}+)\s*'.format(punc_chars), replace_group_with_whitespace, ret_str)
    return ret_str


def remove_final_punctuation(ret_str):
    ret_str = re.sub('({}+)$'.format(punc_chars), replace_group_with_whitespace, ret_str)
    return ret_str


def rejoin_letter(ret_str, letter='t', direction='right'):
    """
    Reattach lone letters hanging out by their lonesome.
    @param ret_str:
    """
    if direction == 'right':
        ret_str = re.sub(r'\s(%s)\s+(\S+)' % letter, r' \1\2', ret_str)
    elif direction == 'left':
        ret_str = re.sub(r'(\S+)\s+(%s)\s' % letter, r'\1\2 ', ret_str)
    else:
        raise Exception('Invalid direction specified!')
    return ret_str


def remove_byte_char(ret_str):
    return re.sub('^b["\']\s+', '', ret_str).strip()

def replace_group_with_whitespace(match_obj):
    """
    :type match_obj: MatchObject
    """
    match_start, match_stop = match_obj.span(1)
    overall_start, overall_stop = match_obj.span(0)

    start_offset = match_start - overall_start
    stop_offset  = (match_stop-match_start) + start_offset

    new_str = '{}{}{}'.format(match_obj.group(0)[:start_offset],
                              ' '*(stop_offset-start_offset),
                              match_obj.group(0)[stop_offset:])

    return new_str

def remove_parenthetical_numbering(ret_str):
    ret_str = re.sub('(\((?:[ivx]+|[a-z]|[1-9\.]+[a-z]?)\))', replace_group_with_whitespace, ret_str)
    # ret_str = re.sub('^\s*(\(.*?\))', replace_group_with_whitespace, ret_str)
    return ret_str


def remove_period_numbering(ret_str):
    """
    Remove period-initial numbering like:
    |
    1.   a.  ii.
    """
    number_search = '^\s*((?:[a-z]|[ivx]+)\.)'.format(list_re)

    return re.sub(number_search, replace_group_with_whitespace, ret_str)



def remove_leading_numbers(ret_str):
    return re.sub('^\s*([0-9]+)', replace_group_with_whitespace, ret_str)


def remove_numbering(ret_str):
    ret_str = remove_parenthetical_numbering(ret_str)
    ret_str = remove_period_numbering(ret_str)
    ret_str = remove_leading_numbers(ret_str)
    return ret_str


def remove_hyphens(ret_str):
    return re.sub('[\-=]', '', ret_str)


def remove_leading_punctuation(ret_str):
    return re.sub('^[%s]+' % string.punctuation, '', ret_str)


def collapse_spaces(ret_str):
    return re.sub('\s+', ' ', ret_str)


# ===============================================================================
# Encode
# ===============================================================================
def rgp(o):
    print(rgencode(o))


def rgencode(o):
    if isinstance(o, Tier):
        return encode_tier(o)
    elif isinstance(o, Item):
        return encode_item(o)
    elif isinstance(o, Igt):
        return encode_igt(o)
    elif isinstance(o, XigtCorpus):
        return ''.join(encode_xigtcorpus(o))
    else:
        raise Exception('%s is not a XIGT object, but is: %s' % (o, type(o)))

def concat_lines(linelist):
    newline = ''
    for line in linelist:
        newline += line[:]
    return newline

def merge_lines(linelist):
    """
    Given two lines, merge characters that fall into blank space on
    the other line.

    @param linelist:
    """

    newline = ''
    blank_spans = []
    for line in linelist:

        # If this is the first line, just make it the newline
        if not newline:
            newline = line[:]

            # Find all the blanks in the newline
            blanks = re.finditer('\s+', newline)
            for blank in blanks:
                blank_spans.append(blank.span())

        # If there is already a newline, look at the non-blank
        # parts of this line and insert them.
        else:
            nonblanks = re.finditer('\S+', line)
            for nonblank in nonblanks:
                nonblank_start, nonblank_stop = nonblank.span()
                nonblank_txt = nonblank.group(0)

                #===============================================================
                # If the nonblank occurs after the end of the original line..
                #===============================================================
                if nonblank_start >= len(newline):
                    oldline = newline[:]
                    newline = ''

                    for i in range(len(line)):
                        if i < nonblank_start and i < len(oldline):
                            newline += oldline[i]
                        elif nonblank_start > i >= len(oldline):
                            newline += ' '
                        else:
                            newline += line[i]
                    continue

                #===============================================================
                # Otherwise, look to see if it can fit inside a blank space.
                #===============================================================

                fits = False
                for blank_start, blank_stop in blank_spans:
                    if nonblank_start >= blank_start and nonblank_stop <= blank_stop:
                        fits = True
                        break

                if fits:
                    # Actually merge the strings
                    oldline = newline[:]  # Copy the old string
                    newline = ''

                    for i in range(len(oldline)):
                        if nonblank_start <= i < nonblank_stop:
                            newline += nonblank_txt[i - nonblank_start]
                        else:
                            newline += oldline[i]

                    # Find all the blanks in the newline
                    blank_spans = []
                    blanks = re.finditer('\s+', newline)
                    for blank in blanks:
                        blank_spans.append(blank.span())

    return newline


#===============================================================================
# Different tiers of cleaning
#===============================================================================

def clean_gloss_string(ret_str):
    # Remove ellipses
    # ret_str = remove_elipses(ret_str)
    ret_str = join_morphs(ret_str)
    ret_str = fix_grams(ret_str)

    # Rejoin letters
    ret_str = rejoin_letter(ret_str, 't', 'right')
    ret_str = rejoin_letter(ret_str, 'h', 'left')

    # Remove word-final punctuation
    # ret_str = remove_external_punctuation(ret_str)

    # Collapse spaces
    # ret_str = collapse_spaces(ret_str)

    # Remove final punctuation
    ret_str = remove_final_punctuation(ret_str)

    # Remove illegal chars
    ret_str = re.sub('(#)', replace_group_with_whitespace, ret_str)

    return ret_str


def clean_trans_string(ret_str):
    # Start by removing the leading "B" stuff
    # ret_str = re.sub('^b["\']', '', trans_string).strip()

    # Remove word-final punctuation:
    # ret_str = remove_external_punctuation(ret_str)

    # Remove solo punctuation
    ret_str = remove_solo_punctuation(ret_str)

    # Remove surrounding quotes and parentheticals
    ret_str = surrounding_quotes_and_parens(ret_str)

    # Remove leading grammaticality markers
    ret_str = grammaticality(ret_str)

    # Remove surrounding quotes and parentheticals
    # ret_str = surrounding_quotes_and_parens(ret_str)

    # t seems to hang out on its own
    ret_str = rejoin_letter(ret_str, letter='t', direction='right')
    ret_str = rejoin_letter(ret_str, letter='h', direction='left')
    ret_str = rejoin_letter(ret_str, letter='e', direction='left')

    # Remove leading numbering
    ret_str = remove_numbering(ret_str)

    # Collapse spaces
    # ret_str = collapse_spaces(ret_str)

    return ret_str

def strip_leading_whitespace(lines):
    """
    Given

    :type lines: list[str]
    """
    newlines = []

    min_leading_whitespace = None

    for line in lines:
        leading_whitespace = re.search('^\s*', line).group(0)
        if min_leading_whitespace is None:
            min_leading_whitespace = len(leading_whitespace)
        else:
            min_leading_whitespace = min(min_leading_whitespace, len(leading_whitespace))

    for line in lines:
        newlines.append(line[min_leading_whitespace:])

    return newlines



def clean_lang_string(ret_str):
    """
    Clean the language string.

    :param ret_str:
    :return:
    """
    # Remove leading byte string
    # ret_str = remove_byte_char(ret_str)

    # First remove leading parenthetical numbering
    ret_str = remove_numbering(ret_str)

    ret_str = surrounding_quotes_and_parens(ret_str)
    # Remove spurious brackets
    ret_str = re.sub('([\[\]\(\)])', replace_group_with_whitespace, ret_str)

    # Split punctuation
    # ret_str = remove_external_punctuation(ret_str)
    # ret_str = split_punctuation(ret_str)

    # Collapse spaces
    # ret_str = collapse_spaces(ret_str)

    # Remove final punctuation
    # ret_str = remove_final_punctuation(ret_str)

    # ret_str = remove_hyphens(ret_str)

    return ret_str

def strict_columnar_alignment(s_a, s_b):
    words_a = list(re.finditer('\S+', s_a))
    words_b = list(re.finditer('\S+', s_b))

    a = Alignment()

    for i, word_a in enumerate(words_a):
        start_a, stop_a = word_a.span()
        for j, word_b in enumerate(words_b):
            start_b, stop_b = word_b.span()

            # CASE 1:
            #    word_a is completely subsumed
            #    by the span of word_b
            if start_a >= start_b and stop_a <= stop_b:
                a.add((i+1, j+1))

            # CASE 2:
            #    word_b is completely subsumed
            #    by the span of word_a
            elif start_b >= start_a and stop_b <= stop_a:
                a.add((i+1, j+1))


    return a

def is_strict_columnar_alignment(s_a, s_b):
    a = strict_columnar_alignment(s_a, s_b)
    return len(a.all_src()) == len(s_a.split()) and len(a.all_tgt()) == len(s_b.split())



# -------------------------------------------
# Search for judgment on line
# -------------------------------------------
def get_judgment(line):
    line, j = extract_judgment(line)
    return j

def extract_judgment(line):
    """
    Given a string, attempt to extract the judgment character ("*" or "?") from it.

    :param line:
    :type line: str
    :return: Tuple of the altered line and the judgment character.
     :rtype: tuple[str, str]
    """
    judgment_re = '^[\s\'\`\"]*([\?\*])'
    result = re.search(judgment_re, line)

    j = None
    if result:
        line = re.sub(judgment_re, replace_group_with_whitespace, line)
        j = result.group(1)
    if '*' in line:
        if j is None:
            j = '*'
        else:
            j+= '*'

    return line, j


#===============================================================================
# Backoff methods
#===============================================================================

def hyphenate_infinitive(ret_str):
    return re.sub('to\s+(\S+)', r'to-\1', ret_str, flags=re.I)

#===============================================================================
# Test Cases
#===============================================================================


class TestLangLines(unittest.TestCase):
    def runTest(self):
        l1  = '  (38)     Este taxista     (*me) parece [t estar cansado]'
        l1c = '           Este taxista      *me  parece  t estar cansado '

        self.assertEqual(clean_lang_string(l1), l1c)

    def keep_something_test(self):
        l1 = ' (1)      Mangi-a.'
        # l1 = '  (1)     Mangi-a.'

        l1_clean = clean_lang_string(l1)
        l1_target = '          Mangi-a '

        self.assertEquals(l1_clean, l1_target)


class TestGlossLines(unittest.TestCase):
    def test_gloss(self):
        g1 = 'Agnès     1SG . REC   3SG . M . THM   present. FUT .3 SG'

        g1_clean = clean_gloss_string(g1)
        g1_target = 'Agnès     1SG.REC   3SG.M.THM   present.FUT.3SG'

        self.assertEquals(g1_clean, g1_target)


class TestHyphenate(unittest.TestCase):
    def runTest(self):
        h1 = 'the guests wanted to visit the other pavilion'
        h1f = 'the guests wanted to-visit the other pavilion'

        self.assertEqual(hyphenate_infinitive(h1), h1f)


class TestMergeLines(unittest.TestCase):
    def runTest(self):
        l1 = 'This        an example          merged lines'
        l2 = '      is         sdfa     of                '

        merged = merge_lines([l1, l2])
        tgt = 'This  is    an example    of    merged lines'
        self.assertEqual(merged, tgt)

from .search import find_in_obj
from intent.alignment.Alignment import Alignment