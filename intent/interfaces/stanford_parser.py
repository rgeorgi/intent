"""
OO interface for communicating with the Stanford Parser

:author: rgeorgi
"""

# Built-in imports -------------------------------------------------------------
import logging

# Internal Imports -------------------------------------------------------------
from intent.utils.env import parser_jar, parser_model, parser_model_jar
from intent.utils.systematizing import ProcessCommunicator

# NLTK Import
from intent.trees import IdTree, DepTree, TreeError
import unittest


# Set up the parser logger -----------------------------------------------------
PARSE_LOG = logging.getLogger('STANFORD_PARSER')

def parser_stderr_handler(msg):
    if   msg.startswith('Loading parser from serialized'): PARSE_LOG.info(msg)
    elif msg.startswith('Parsing file:'): PARSE_LOG.info(msg)
    elif msg.startswith('Parsing [sent.'): PARSE_LOG.info(msg)
    else:
        PARSE_LOG.warn(msg)

class ParseResult(object):
    def __init__(self):
        self.pt = None
        self.dt = None

class StanfordParser(object):
    """
    Instantiate an object which can be called upon to return either phrase structure parses or
    dependency parses.
    """
    def __init__(self):
        self.p = ProcessCommunicator(['java', '-Xmx1200m',
                                        '-cp', parser_jar+':'+parser_model_jar,
                                        'edu.stanford.nlp.parser.lexparser.LexicalizedParser',
                                        '-outputFormat', 'penn,typedDependencies',
                                        '-sentences', 'newline',
                                        '-tokenized',
                                        parser_model,
                                        '-'], stderr_func=parser_stderr_handler)

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



# 	def test_phrase(self):
# 		
# 		a = IdTree.fromstring('(ROOT (S (NP (NNP John)) (VP (VBD ran) (PP (IN into) (NP (DT the) (NNS woods))))))')
# 		self.assertEqual(self.r.pt, a)

    def test_deptree(self):
        print(self.r.dt)