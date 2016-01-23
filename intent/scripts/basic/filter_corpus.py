from multiprocessing.pool import Pool
import os

from multiprocessing import Lock

from intent.igt.rgxigt import RGCorpus, sort_corpus
from xigt.codecs import xigtxml

__author__ = 'rgeorgi'

import logging
logging.getLogger()
FILTER_LOG = logging.getLogger('FILTERING')

def filter_instance(path, require_lang, require_gloss, require_trans, require_aln, require_gloss_pos):

    filtered_instances = []

    FILTER_LOG.info("Loading file {}".format(os.path.basename(path)))
    xc = RGCorpus.load(path)

    old_num = len(xc)

    if require_trans:
        xc.require_trans_lines()
    if require_gloss:
        xc.require_gloss_lines()
    if require_lang:
        xc.require_lang_lines()
    if require_aln:
        xc.require_one_to_one()
    if require_gloss_pos:
        xc.require_gloss_pos()

    for inst in xc:
        filtered_instances.append(inst)

    new_num = len(xc)

    FILTER_LOG.info("{} instances added. {} filtered out.".format(new_num, old_num - new_num))
    return filtered_instances



def filter_corpus(filelist, outpath, require_lang=True, require_gloss=True, require_trans=True, require_aln=True, require_gloss_pos=False):
    new_corp = RGCorpus()

    pool = Pool(4)

    l = Lock()
    def merge_to_new_corp(inst_list):
        l.acquire()
        for inst in inst_list:
            new_corp.append(inst)
        l.release()

    for f in filelist:
        # pool.apply_async(filter_instance, args=[f, require_lang, require_gloss, require_trans, require_aln, require_gloss_pos], callback=merge_to_new_corp)
        merge_to_new_corp(filter_instance(f, require_lang, require_gloss, require_trans, require_aln, require_gloss_pos))

    pool.close()
    pool.join()

    try:
        os.makedirs(os.path.dirname(outpath))
    except (FileExistsError, FileNotFoundError) as fee:
        pass

    # Only create a file if there are some instances to create...
    if len(new_corp) > 0:

        f = open(outpath, 'w', encoding='utf-8')

        print("Writing out {} instances...".format(len(new_corp)))
        sort_corpus(new_corp)
        xigtxml.dump(f, new_corp)
        f.close()

    else:
        print("No instances remain after filtering. Skipping.")