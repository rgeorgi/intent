"""
Build a dictionary from slashtag files.
"""

# Built-in imports -------------------------------------------------------------
import argparse

# Internal imports -------------------------------------------------------------
from multiprocessing.pool import Pool
import os
import pickle
from multiprocessing import cpu_count
from intent.corpora.POSCorpus import process_slashtag_file, process_wsj_file
from intent.pos.TagMap import TagMap
from intent.utils.argutils import existsfile, globfiles
from intent.utils.dicts import POSEvalDict
from intent.utils.listutils import flatten_list



def process_file(path, tm):

    c = POSEvalDict()

    def add_to_dict(tokens):
        for token in tokens:

            # Do the tagset remapping.
            if tm is not None:
                label = tm[token.label]
            else:
                label = token.label

            c.add(token.seq.lower(), label)

    print('Reading file "{}"'.format(os.path.basename(path)))
    ext = os.path.splitext(path)[1]

    # If the specified file extension is ".mrg", treat it as a WSJ file.
    if ext == '.mrg':
        cur_token_count, cur_linecount = process_wsj_file(path, add_to_dict)

    # Otherwise, assume it is a slashtag file.
    else:
        cur_token_count, cur_linecount = process_slashtag_file(path, add_to_dict, delimeter=delimeter)

    return c, cur_token_count, cur_linecount

def create_dictionary(filelist, output, tagmap, delimeter = '/'):
    """
    Create a dictionary out of slashtag-based files.

    :param filelist: List of file paths
    :type filelist: list[str]
    :param output: output file path
    :type output: str
    :param tagmap: Optional
    :type tagmap: TagMap
    """
    c = POSEvalDict()



    counts = {'tokens':0, 'lines':0}

    def merge_counts(result):
        d, cur_tokencount, cur_linecount = result
        c.combine(d)
        counts['tokens'] += cur_tokencount
        counts['lines'] += cur_linecount

    tm = None
    if tagmap:
        tm = TagMap(tagmap)

    # Initialize multithreading...
    p = Pool(cpu_count())
    for path in filelist:
        p.apply_async(process_file, args=[path, tm], callback=merge_counts)
        # result = p.apply(process_file, args=[path, tm])
        # process_file(path)

    p.close()
    p.join()


    # Now, dump the pickled POSEvalDict.
    print("Writing out dictionary...", end=' ')
    pickle.dump(c, open(output, 'wb'))
    print("Done.")
    print("{} tokens processed, {} sentences.".format(counts['tokens'], counts['lines']))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('FILE', nargs='+', help='Slashtag files for input', type=globfiles)
    p.add_argument('-o', dest='output', help='Destination for pickled POS dict', required=True)
    p.add_argument('-t', '--tagmap', help='Tag Map for tags', type=existsfile)

    args = p.parse_args()

    create_dictionary(flatten_list(args.FILE), args.output, args.tagmap)