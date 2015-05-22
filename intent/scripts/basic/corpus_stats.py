'''
Created on Mar 21, 2014

@author: rgeorgi

Scripts for gathering general information on the various POS corpora being used. 

Basic analysis such as word types, number of types of POS tag, and the percentage
that each make up of things.
'''

# Set up logging.
import logging
from multiprocessing.pool import Pool
import os, argparse, sys
import intent.utils.env
from intent.igt.igtutils import rgp


STATS_LOGGER = logging.getLogger(__name__)

#===============================================================================
# IMPORTS
#===============================================================================

from collections import defaultdict

from intent.igt.rgxigt import RGCorpus, NoLangLineException, XigtFormatException,\
    GlossLangAlignException
from intent.igt import rgxigt
from intent.utils.dicts import StatDict
from intent.utils.token import tokenize_string, tag_tokenizer
from intent.utils.argutils import writefile

#===========================================================================
# Get XIGT logging info....
#===========================================================================
xigt_logger = logging.getLogger(rgxigt.__name__)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
xigt_logger.addHandler(sh)
xigt_logger.setLevel(logging.ERROR)

#  -----------------------------------------------------------------------------

def inst_stats(igt):

    igts = defaultdict(int)
    types = defaultdict(lambda: defaultdict(int))

    #=======================================================================
    # Count the text on the lines
    #=======================================================================
    def igt_line_count(igt, attr):
        try:
            line = getattr(igt, attr)
        except XigtFormatException as tpe:
            line = False

        if line:
            igts[attr+'_lines'] += 1
            igts[attr+'_tokens'] += len(line)
            for token in line:
                types[attr+'_types'][token.get_content().lower()] += 1

    dict = {}
    # Count the language lines -----------------------------------------
    igt_line_count(igt, 'lang')
    igt_line_count(igt, 'gloss')
    igt_line_count(igt, 'trans')

    try:
        igt.trans
        igt.gloss
        igt.lang
    except XigtFormatException as tpe:
        pass
    else:
        igts['all_lines'] += 1
        try:
            igt.get_gloss_lang_alignment()
        except GlossLangAlignException as glae:
            pass
        else:
            igts['1-to-1'] += 1

    igts['instances'] += 1

    return (types, igts)



def igt_stats(filelist, type='text', logpath=None):

    # Set up the headers -------------------------------------------------------
    cols = ['language','instances','all_lines','g-l-1-to-1']
    keys = ['lang', 'gloss', 'trans']
    for k in keys:
        lin = k+'_lines'
        tok = k+'_tokens'
        typ = k+'_types'
        cols += [lin, tok, typ]
    print(','.join(cols))

    # Load the corpus.
    for path in filelist:

        row = [os.path.splitext(os.path.basename(path))[0]]

        igts = defaultdict(int)
        types = defaultdict(lambda: defaultdict(int))

        if type == 'xigt':
            STATS_LOGGER.info('Processing xigt file: "%s"' % path)
            rc = RGCorpus.load(path)

        elif type == 'text':
            STATS_LOGGER.info('Processing text file: "%s"' % path)
            rc = RGCorpus.from_txt(path, require_1_to_1=False)


        def merge_dicts(result):
            # Unpack the result...
            new_types, new_igts = result

            # Now, add the dicts together...
            igts['all_lines'] += new_igts['all_lines']
            igts['instances'] += new_igts['instances']
            igts['1-to-1'] += new_igts['1-to-1']
            for attr in ['lang','gloss','trans']:
                igts[attr+'_lines'] += new_igts[attr+'_lines']
                igts[attr+'_tokens'] += new_igts[attr+'_tokens']
                types[attr+'_types'] += new_types[attr+'_types']

        pool = Pool(8)
        for igt in rc:
            pool.apply_async(inst_stats, args=[igt], callback=merge_dicts)

        pool.close()
        pool.join()


        row += [igts['instances'], igts['all_lines'], igts['1-to-1']]
        for k in keys:
            lin = k+'_lines'
            tok = k+'_tokens'
            typ = k+'_types'

            row += [igts[lin], igts[tok], len(types[typ])]

        # Make them all into strings
        row = [str(i) for i in row]

        print(','.join(row))


def pos_stats(filelist, tagged, log_file = sys.stdout, csv=False):

    # Count of each unique word and its count.
    wordCount = StatDict()

    # Count of each unique tag and its count.
    tagCount = StatDict()

    # For each POS tag, the number of total
    # words used in that count.
    typetags = StatDict()

    # Count of each unique tag and the word types associated with it.
    tagtypes = defaultdict(set)

    # Count the number of lines
    lines = 0

    for filename in filelist:
        f = open(filename, 'r', encoding='utf-8')
        for line in f:
            lines += 1
            tokens = tokenize_string(line, tokenizer=tag_tokenizer)
            for token in tokens:

                seq = token.seq.lower()

                if seq not in wordCount:
                    typetags[token.label] += 1

                wordCount[seq] += 1
                tagCount[token.label] += 1

                # Start counting the average types per tag.
                tagtypes[seq] |= set([token.label])


    # Calculate tags per type
    type_sum = 0.
    for word in tagtypes.keys():
        type_sum += len(tagtypes[word])

    if len(tagtypes) == 0:
        tag_per_type_avg = 0
    else:
        tag_per_type_avg = type_sum / len(tagtypes)

    #===========================================================================
    # Get the stats we want to return
    #===========================================================================

    total_tokens = wordCount.total
    total_types = len(wordCount)

    if not csv:
        log_file.write('Sentences    : %d\n' % lines)
        log_file.write('Total Tokens : %d\n' % total_tokens)
        log_file.write('Total Types  : %d\n' % total_types)
        log_file.write('Avg Tags/Type: %.2f\n' % tag_per_type_avg)
    else:
        log_file.write('sents,tokens,types,tags-per-type\n')
        log_file.write('%s,%s,%s,%.2f\n' % (lines, total_tokens, total_types, tag_per_type_avg))


    log_file.write('\n'* 2 + '='*80 + '\n')

    labels = list(tagCount.keys())
    labels = sorted(labels)


    log_file.write('tag, tag_counts, types_per_tag, percent_of_tokens, percent_of_types\n')
    for i, tag in enumerate(labels):
        tagcounts = tagCount[tag]
        typetagcounts = typetags[tag]

        percent_tokens = float(tagcounts) / wordCount.total * 100
        percent_types = float(typetagcounts) / len(wordCount)* 100

        log_file.write('%s,%d,%d,%.2f,%0.2f\n' % (tag, tagcounts, typetagcounts, percent_tokens, percent_types))

#===============================================================================
# MAIN
#===============================================================================

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--slashtags', nargs='*', default=[])
    p.add_argument('--xigt', nargs='*', default=[])
    p.add_argument('--igt-txt', nargs='*', default=[])
    p.add_argument('--tagged', default=True)
    p.add_argument('--log', type=str)
    p.add_argument('--csv', action='store_true', default=True)

    args = p.parse_args()

    #===========================================================================
    # Our own logging info...
    #===========================================================================
    if args.log:
        STATS_LOGGER.addHandler(logging.FileHandler(args.log))
    else:
        STATS_LOGGER.addHandler(logging.StreamHandler())

    STATS_LOGGER.setLevel(logging.INFO)
    #  -----------------------------------------------------------------------------


    igt_stats(args.xigt, type='xigt')
    igt_stats(args.igt_txt, type='text')

    for f in args.slashtags:
        sys.stderr.write('\n\n\n\n\n\n%s\n' % f)
        pos_stats([f], args.tagged, log_file = sys.stderr, csv=args.csv)
