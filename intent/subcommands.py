"""
Created on Mar 24, 2015

@author: rgeorgi
"""

import logging
from io import StringIO

from intent.scripts.igt.extract_lang import extract_lang
from intent.scripts.conversion.odin_to_xigt import parse_text
from intent.utils.env import odin_data

#===============================================================================
# The ODIN subcommand
#===============================================================================


def odin(**kwargs):
    ODIN_LOG = logging.getLogger('ODIN')

    odin_txt = StringIO()
    print('Extracting languages matching "%s" from ODIN.' % kwargs.get('LNG'))
    extract_lang(odin_data, kwargs.get('LNG'), odin_txt, limit=kwargs.get('limit'))
    odin_txt_data = odin_txt.getvalue()

    print(kwargs.get('out_file'))

    if kwargs.get('format') == 'txt':
        f = open(kwargs.get('OUT_FILE'), 'w', encoding='utf-8')
        f.write(odin_txt_data)
    else:
        f = open(kwargs.get('OUT_FILE'), 'w', encoding='utf-8')

        parse_text(StringIO(odin_txt_data), f)


