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
import os
import argparse
import sys
from multiprocessing import cpu_count
from intent.trees import read_conll_file
from intent.utils.fileutils import globlist

from intent.utils.listutils import chunkIt

STATS_LOGGER = logging.getLogger(__name__)
#STATS_LOGGER.setLevel(logging.INFO)

#===============================================================================
# IMPORTS
#===============================================================================

from collections import defaultdict

from intent.igt.rgxigt import RGCorpus, RGIgt, MultipleNormLineException, NoGlossLineException, NoLangLineException, \
    NoTransLineException
from intent.utils.dicts import StatDict, CountDict, TwoLevelCountDict
from intent.utils.token import tokenize_string, tag_tokenizer

#===========================================================================
# Get XIGT logging info....
#===========================================================================
xigt_logger = logging.getLogger("RGXIGT")
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
xigt_logger.addHandler(sh)
xigt_logger.setLevel(logging.ERROR)


CONLL_TYPE = 'conll'
SLASHTAG_TYPE = 'slashtags'

#  -----------------------------------------------------------------------------




def avg_tags_per_word(word_tag_dict):
    wt_counts = [len(word_tag_dict[word]) for word in word_tag_dict.keys()]
    return sum(wt_counts) / len(wt_counts)


class IGTStatDict(object):
    def __init__(self):
        self.instances = 0
        self.corrupt_instances = 0
        self.double_column_instances = 0
        self.lang = CountDict()
        self.gloss = CountDict()
        self.trans = CountDict()

        self.lang_tags = TwoLevelCountDict()
        self.gloss_tags = TwoLevelCountDict()
        self.trans_tags = TwoLevelCountDict()

        self.lang_word_tags = TwoLevelCountDict()
        self.gloss_word_tags = TwoLevelCountDict()
        self.trans_word_tags = TwoLevelCountDict()


    @staticmethod
    def header():
        keys = ['instances',
                'lang_types', 'lang_tokens',
                'gloss_types','gloss_tokens',
                'lang_types','lang_tokens','corrupt_instances','double_column_instances']

        return ','.join(keys)

    def __str__(self):
        # instances, lang_types, lang_tokens, gloss_types, gloss_tokens, trans_types, trans_tokens
        return '{},{},{},{},{},{},{},{},{}'.format(self.instances,
                                                   len(self.lang), self.lang.total(),
                                                   len(self.gloss), self.gloss.total(),
                                                   len(self.trans), self.trans.total(),
                                                   self.corrupt_instances, self.double_column_instances)

    def combine(self, other):
        """

        :type other: IGTStatDict
        """

        self.instances += other.instances
        self.corrupt_instances += other.corrupt_instances
        self.double_column_instances += other.double_column_instances

        self.lang += other.lang
        self.gloss += other.gloss
        self.trans += other.trans
        
        self.gloss_tags += other.gloss_tags
        self.lang_tags += other.lang_tags
        self.trans_tags += other.trans_tags

        self.gloss_word_tags += other.gloss_word_tags
        self.lang_word_tags += other.lang_word_tags
        self.trans_word_tags += other.trans_word_tags

def count_words_tags(inst, tier, word_dict, tag_dict, word_tag_dict):
    """

    :type inst: RGIgt
    """
    # Now, add the words...
    for word in tier:
        word_dict.add(word.value().lower())

    # Now, count the tags...
    pos_tier = inst.get_pos_tags(tier.id)
    if pos_tier is not None:
        for tag in pos_tier:
            tag_val = tag.value()

            # If there are more POS tags than words,
            # we may occasionally get this "broken"  system.
            wrd_aln = inst.find(id = tag.alignment)
            if wrd_aln:
                wrd_val = wrd_aln.value()
                tag_dict.add(tag_val, wrd_val)
                word_tag_dict.add(wrd_val, tag_val)




def inst_list_stats(inst_list):
    """

    :type inst_list: list[RGIgt]
    """
    sd = IGTStatDict()

    for inst in inst_list:

        sd.instances += 1

        if inst.has_corruption():
            sd.corrupt_instances += 1

        if inst.has_double_column():
            sd.double_column_instances += 1

        try:
            count_words_tags(inst, inst.lang, sd.lang, sd.lang_tags, sd.lang_word_tags)
        except (MultipleNormLineException, NoLangLineException) as e:
            STATS_LOGGER.info(str(e))

        try:
            count_words_tags(inst, inst.gloss, sd.gloss, sd.gloss_tags, sd.gloss_word_tags)
        except (MultipleNormLineException, NoGlossLineException) as e:
            STATS_LOGGER.info(str(e))

        try:
            count_words_tags(inst, inst.trans, sd.trans, sd.trans_tags, sd.trans_word_tags)
        except (MultipleNormLineException, NoTransLineException) as e:
            STATS_LOGGER.info(str(e))

    return sd



def igt_stats(filelist, type='text', logpath=None, show_header=True, show_filename=False):

    sd = IGTStatDict()

    # Load the corpus.
    for path in filelist:

        row = [os.path.splitext(os.path.basename(path))[0]]

        if type == 'xigt':
            STATS_LOGGER.info('Processing xigt file: "%s"' % path)
            rc = RGCorpus.load(path)


        elif type == 'text':
            STATS_LOGGER.info('Processing text file: "%s"' % path)
            rc = RGCorpus.from_txt(path)

        pool = Pool(cpu_count())

        # Divide the file into roughly equal chunks
        chunks = chunkIt(rc.igts, cpu_count())

        for chunk in chunks:
            pool.apply_async(inst_list_stats, args=[chunk], callback=sd.combine)
            # sd.combine(inst_list_stats(chunk))


        pool.close()
        pool.join()

    if show_header:
        print(sd.header())

    words = sorted(sd.gloss_word_tags.keys(), key=lambda x: sd.gloss_word_tags[x].total(), reverse=True)[:100]

    if show_filename:
        print(os.path.splitext(os.path.basename(path))[0], end=',')

    # for word in words:
    #     countdict = sd.gloss_word_tags[word]
    #     print('{},{},{}'.format(word, countdict.total(), countdict))


    print(sd)

class UndefinedPOSTypeError(Exception): pass

def pos_stats(filelist, filetypes=SLASHTAG_TYPE, log_file = sys.stdout, csv=False):

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

    sents = []
    # =============================================================================
    # Slashtags File
    # =============================================================================
    if filetypes == SLASHTAG_TYPE:
        for filename in filelist:
            f = open(filename, 'r', encoding='utf-8')
            for line in f:
                lines += 1

                sents.append(tokenize_string(line, tokenizer=tag_tokenizer))

    elif filetypes == CONLL_TYPE:
        for filename in filelist:
            trees = read_conll_file(filename)
            for tree in trees:
                sents.append(tree.pos_list())

    else:
        raise UndefinedPOSTypeError('Unknown POS filetype "{}"'.format(filetypes))

    # =============================================================================
    # Now process the sentences
    # =============================================================================

    for tokens in sents:
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
        log_file.write('Sentences    : %d\n' % len(sents))
        log_file.write('Total Tokens : %d\n' % total_tokens)
        log_file.write('Total Types  : %d\n' % total_types)
        log_file.write('Avg Tags/Type: %.2f\n' % tag_per_type_avg)
    else:
        log_file.write('sents,tokens,types,tags-per-type\n')
        log_file.write('%s,%s,%s,%.2f\n' % (len(sents), total_tokens, total_types, tag_per_type_avg))


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
    p.add_argument('--slashtags', nargs='*', default=[], type=globlist)
    p.add_argument('--conll', nargs='*', default=[])
    p.add_argument('--xigt', nargs='*', default=[])
    p.add_argument('--igt-txt', nargs='*', default=[])
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


    #  -----------------------------------------------------------------------------


    igt_stats(args.xigt, type='xigt')
    igt_stats(args.igt_txt, type='text')

    for f in args.slashtags:
        sys.stderr.write('\n\n\n\n\n\n%s\n' % f)
        pos_stats([f], log_file = sys.stderr, csv=args.csv)

    if args.conll:
        pos_stats(args.conll, filetypes=CONLL_TYPE, csv=args.csv)
