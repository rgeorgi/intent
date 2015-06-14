"""
Module to help dealing with "grams" (sub-token level gloss-line elements)
"""
import sys
import re
import logging

from intent.utils import env
from intent.utils.argpasser import ArgPasser

# ===============================================================================
# Initialize logging
# ===============================================================================

MODULE_LOGGER = logging.getLogger(__name__)

gramdict = {'1sg': ['i', 'me'],
            'det': ['the'],
            '3pl': ['they'],
            '3sg': ['he', 'she', 'him', 'her'],
            '3sgf': ['she', 'her'],
            '2sg': ['you'],
            '3sgp': ['he'],
            'poss': ['his', 'her', 'my', 'their'],
            'neg': ["n't", 'not'],
            '2pl': ['you']}


def sub_grams(gram):
    if gram in gramdict:
        return gramdict[gram]
    else:
        return [gram]

# ===============================================================================
# Write Gram
# ===============================================================================


def write_gram(token, **kwargs):

    # Re-cast the kwargs as an argpasser.
    kwargs = ArgPasser(kwargs)

    output_type = kwargs.get('type', 'classifier')
    output = kwargs.get('output', sys.stdout)

    posdict = kwargs.get('posdict', None)

    if posdict is None:
        posdict = env.posdict

    # Previous tag info
    prev_gram = kwargs.get('prev_gram')
    next_gram = kwargs.get('next_gram')



    # Get heuristic alignment
    aln_labels = kwargs.get('aln_labels', [])

    # ===========================================================================
    # Break apart the token...
    # ===========================================================================
    gram = token.seq

    pos = token.goldlabel

    # Lowercase if asked for
    lower = kwargs.get('lowercase', True, bool)
    gram = gram.lower() if gram else gram

    # A gram should never contain whitespace...
    gram = re.sub('\s', '', gram)

    # ===========================================================================
    # Do some cleaning on the gram....
    # ===========================================================================

    # Only take the first of two slashed grams
    gram = re.sub('(.*)?/(.*)', r'\1', gram)

    # Remove leading and trailing stuff
    gram = re.sub('^(\S+)[\-=:\[\(\]\)/\*]$', r'\1', gram)
    gram = re.sub('^[\-=:\[\(\]\)/\*](\S+)$', r'\1', gram)

    # ===========================================================================

    # Output the grams for a classifier
    #
    # NOTE! Only tokens that have an ASSIGNED pos tag will be written out this way!
    if output_type == 'classifier' and pos:
        output.write(pos)

        # =======================================================================
        # Get the morphemes
        # =======================================================================

        morphs = intent.utils.token.tokenize_string(gram, intent.utils.token.morpheme_tokenizer)

        # Replace the characters that cause the svmlight format issues.
        gram = gram.replace(':', '-')

        # =======================================================================
        # Is there a number
        # =======================================================================
        if re.search('[0-9]', gram) and kwargs.get('feat_has_number', False, bool):
            output.write('\thas-number:1')

        # =======================================================================
        # What labels is it aligned with
        # =======================================================================
        if kwargs.get('feat_align', False, bool):
            for aln_label in aln_labels:
                output.write('\taln-label-%s:1' % aln_label)

        # =======================================================================
        # Suffix
        # =======================================================================
        if kwargs.get('feat_suffix', True, bool):
            output.write('\tgram-suffix-3-%s:1' % gram[-3:])
            output.write('\tgram-suffix-2-%s:1' % gram[-2:])
            output.write('\tgram-suffix-1-%s:1' % gram[-1:])

        # =======================================================================
        # Prefix
        # =======================================================================
        if kwargs.get('feat_prefix', True, bool):
            output.write('\tgram-prefix-3-%s:1' % gram[:3])
            output.write('\tgram-prefix-2-%s:1' % gram[:2])
            output.write('\tgram-prefix-1-%s:1' % gram[:1])

        # =======================================================================
        # Number of morphs
        # =======================================================================
        if kwargs.get('feat_morph_num', False, bool):
            output.write('\t%d-morphs:1' % len(morphs))

        # ===================================================================
        # Previous gram
        # ===================================================================
        if prev_gram and kwargs.get('feat_prev_gram', True, bool):
            prev_gram = prev_gram.lower() if lower else prev_gram

            # And then tokenize...
            for token in intent.utils.token.tokenize_string(prev_gram, intent.utils.token.morpheme_tokenizer):

                if kwargs.get('feat_prev_gram', True, bool):
                    output.write('\tprev-gram-%s:1' % token.seq)

                # Add prev dictionary tag
                if posdict and kwargs.get('feat_prev_gram_dict', True, bool) and token.seq in posdict:
                    prev_tags = posdict.top_n(token.seq)
                    output.write('\tprev-gram-dict-tag-%s:1' % prev_tags[0][0])

        # Write a "**NONE**" for prev or next...
        elif kwargs.get('feat_prev_gram', True, bool):
            output.write('\tprev-gram-**NONE**:1')

        # ===================================================================
        # Next gram
        # ===================================================================
        if next_gram and kwargs.get('feat_next_gram', True, bool):
            next_gram = next_gram.lower() if lower else next_gram
            for token in intent.utils.token.tokenize_string(next_gram, intent.utils.token.morpheme_tokenizer):

                # ===================================================================
                # Gram itself
                # ===================================================================

                if kwargs.get('feat_next_gram', True, bool):
                    output.write('\tnext-gram-%s:1' % token.seq)

                if posdict and kwargs.get('feat_next_gram_dict', True, bool) and token.seq in posdict:
                    next_tags = posdict.top_n(token.seq)
                    output.write('\tnext-gram-dict-tag-%s:1' % next_tags[0][0])

        elif kwargs.get('feat_next_gram', True, bool):
            output.write('\tnext-gram-**NONE**:1')

        # =======================================================================
        # Iterate through the morphs
        # =======================================================================

        for token in morphs:
            # ===================================================================
            # Just write the morph
            # ===================================================================
            if kwargs.get('feat_basic', True, bool):
                output.write('\t%s:1' % token.seq)

            # ===================================================================
            # If the morph resembles a word in our dictionary, give it
            # a predicted tag
            # ===================================================================

            if posdict and token.seq in posdict and kwargs.get('feat_dict', True, bool):

                top_tags = posdict.top_n(token.seq)
                # best = top_tags[0][0]
                # if best != pos:
                # 	MODULE_LOGGER.debug('%s tagged as %s not %s' % (gram, pos, best))

                output.write('\ttop-dict-word-%s:1' % top_tags[0][0])
                if len(top_tags) > 1:
                    output.write('\tnext-dict-word-%s:1' % top_tags[1][0])

        output.write('\n')

    # ===========================================================================
    # If writing the gram out for the tagger...
    # ===========================================================================

    if output_type == 'tagger' and kwargs.get('tag_f'):
        output.write('%s/%s ' % (gram, pos))

import intent.utils.token
