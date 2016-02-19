"""
OO interface for communicating with the Stanford Parser

:author: rgeorgi
"""

# Built-in imports -------------------------------------------------------------
import logging

# Internal Imports -------------------------------------------------------------
import os
from glob import glob

from intent.utils.env import parser_dir, parser_model, java_bin
from intent.utils.systematizing import ProcessCommunicator

# NLTK Import
from intent.trees import IdTree, DepTree, TreeError
import unittest


# Set up the parser logger -----------------------------------------------------
PARSE_LOG = logging.getLogger('STANFORD_PARSER')

def parser_stderr_handler(msg):
    if   msg.startswith('Loading parser from serialized'): PARSE_LOG.info(msg)
    elif msg.startswith('Parsing file:'): PARSE_LOG.debug(msg)
    elif msg.startswith('Parsing [sent.'): PARSE_LOG.debug(msg)
    else:
        PARSE_LOG.warn(msg)

class ParseResult(object):
    def __init__(self):
        self.pt = None
        self.dt = None

def parse_interpreter(str, parse_queue):
    parse_queue.append(str)


class StanfordParser(object):
    """
    Instantiate an object which can be called upon to return either phrase structure parses or
    dependency parses.
    """
    def __init__(self):
        jars = glob(os.path.join(parser_dir, "*.jar"))

        self.parse_queue = ''
        args = [java_bin, '-Xmx4096m',
                '-cp', ':'.join(jars),
                'edu.stanford.nlp.parser.lexparser.LexicalizedParser',
                '-outputFormat', 'penn,typedDependencies',
                '-sentences', 'newline',
                '-tokenized',
                parser_model,
                '-']
        PARSE_LOG.debug(' '.join(args))
        self.p = ProcessCommunicator(args, stderr_func=parser_stderr_handler,
                                     blocking=True)

    def parse_interpreter(self, str):
        print(str)

    def parse(self, string, id_base = None):
        """
        Use the parser to parse the given string, and parse it for both dependency tree and phrase structure trees.

        :param string: String to parse
        :type string: str
        :param id_base:
        :type id_base:
        """

        self.p.stdin.write(bytes(string+'\n', encoding='utf-8'))
        self.p.stdin.flush()

        result = ParseResult()
        string = ''


        while True:
            line = self.p.stdout.readline().decode('utf-8', errors='replace').strip()

            # If the line is empty, the first time that means we are switching from phrase structure to
            # dependency. Otherwise, we are done.
            if not line:

                if result.pt:
                    try:
                        result.dt = DepTree.fromstring(string, id_base = 'ds')
                    except TreeError as te:
                        PARSE_LOG.error(te)
                    break
                else:
                    result.pt = IdTree.fromstring(string, id_base = 'ps')
                    string = ''

            string += line+' '

        return result

    def close(self):
        self.p.kill()

class ParseTest(unittest.TestCase):


    def setUp(self):
        self.sp = StanfordParser()
        self.r = self.sp.parse('John ran into the woods')
        self.sp.close()

