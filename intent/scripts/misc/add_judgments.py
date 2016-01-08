import os
from argparse import ArgumentParser
from os import makedirs
import logging
JUDG_LOG = logging.getLogger("JUDGMENTS")

from intent.igt.consts import ODIN_TYPE, ODIN_JUDGMENT_ATTRIBUTE
from xigt import xigtpath

from intent.igt.igtutils import rgp, judgment
from xigt.codecs import xigtxml
from xigt.consts import INCREMENTAL

if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('FILE', nargs='+')
    p.add_argument('-d', '--dest', required=True, help='Output directory for modified files.')
    p.add_argument('-f', '--force', help='Force overwrite existing files.')

    args = p.parse_args()

    for path in args.FILE:
        with open(path, 'r', encoding='utf-8') as f:
            xc = xigtxml.load(f, mode=INCREMENTAL)

            for inst in xc:
                JUDG_LOG.info('Processing instance "{}"'.format(inst.id))
                for item in xigtpath.findall(inst, 'tier[@type='+ODIN_TYPE+']/item'):

                    # Skip blank lines
                    if item.value() is None:
                        continue

                    # Get the judgment and add it if it is non-null.
                    j = judgment(item.value())
                    if j is not None:
                        item.attributes[ODIN_JUDGMENT_ATTRIBUTE] = j
                        JUDG_LOG.debug('Judgment found on item "{}"'.format(item.id))

            # Make the output directory if it doesn't exist.
            makedirs(args.dest, exist_ok=True)
            outpath = os.path.join(args.dest, os.path.basename(path))

            if not os.path.exists(outpath) or args.force:
                with open(outpath, 'w', encoding='utf-8') as out_f:
                    xigtxml.dump(out_f, xc)
