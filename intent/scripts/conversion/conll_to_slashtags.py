'''
Created on Sep 12, 2014

@author: rgeorgi
'''

# Global Imports ---------------------------------------------------------------
import argparse
import os

# Internal imports -------------------------------------------------------------
from intent.corpora.POSCorpus import POSCorpus

def conll_to_slashtags(infiles, outpath):
    '''
    This will
    @param infiles: A list of CONLL pathnames to convert.
    @param outpath: A single output pathname for the slashtags.
    '''
    main_c = POSCorpus()
    for f in infiles:
        from intent.corpora.conll import ConllCorpus
        cp = ConllCorpus()
        c = cp.parse_file(root=f)
        main_c.extend(c)

    st = c.slashtags('/', lowercase=True)

    # Create the containing path if it doesn't already exist
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    of = open(outpath, 'w', encoding='utf-8')
    of.write(st)
    of.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument(metavar='FILE', dest='filelist', nargs='+')
    p.add_argument('-o', dest='outpath', required=True)

    args = p.parse_args()

    conll_to_slashtags(args.filelist, args.outpath)

