"""
Created on Dec 19, 2014

@author: rgeorgi

This script is used to point at a dump of the ODIN database and extract the specified language from it.
"""

# Built-in imports -------------------------------------------------------------
import argparse, re, logging

EXTR_LOG = logging.getLogger('LANG_EXTRACTOR')

# Internal imports -------------------------------------------------------------
from intent.utils.argutils import configfile, writefile
from intent.utils.fileutils import matching_files

def extract_lang(dir, lang, outfile, limit=None):
    
    i = 0
    EXTR_LOG.info('Extracting language "%s" from ODIN...' % lang)

    # Iterate through each ".check" file in the given directory.
    for path in matching_files(dir, '.*\.check$', recursive=True):

        EXTR_LOG.debug('Working on path... "%s"' % path)

        # Open up the file...
        f = open(path, 'r', encoding='latin-1')
        data = f.read()
        f.close()

        # And get the list of instances.
        instances = re.split('\n\n+', data)

        # Remove blank "instances"
        instances = [i for i in instances if i.strip()]

        # Now, for each instance, look for the language.
        for instance in instances[1:]: # <-- skip the first pgph, because it's not an instance.

            inst_lang = None
            # First, if there is a "gold" lang code, use that one.
            gold_re = re.search('gold_lang_code:.*?\(([a-z:]+)\)', instance, flags=re.I)
            chosen_re = re.search('stage3_lang_chosen:.*?\(([a-z:]+)\)', instance, flags=re.I)

            if gold_re:
                inst_lang = gold_re.group(1)

            elif chosen_re:
                inst_lang = chosen_re.group(1)

            if inst_lang == lang:
                outfile.write(instance+'\n\n')
                i += 1
                if limit and i == limit: break

        if limit and i == limit: break

    EXTR_LOG.info('%d instances written.' % i)


if __name__ == '__main__':
    p = argparse.ArgumentParser()

    p.add_argument('-c', '--config', type=configfile)
    p.add_argument('-d', '--dir', help="Path to the ODIN database directory.", required=True)
    p.add_argument('-l', '--lang', help="Language to search for.", required=True)
    p.add_argument('-o', '--outfile', help="Text file which to output the resulting instances to.", required=True, type=writefile)

    args = p.parse_args()

    extract_lang(args.dir, args.lang, args.outfile)