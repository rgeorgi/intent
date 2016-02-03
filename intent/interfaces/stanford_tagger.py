"""
Created on Oct 22, 2013

@author: rgeorgi
"""

import os, sys, re, unittest, time, logging
import subprocess as sub
from optparse import OptionParser

# Internal Imports -------------------------------------------------------------
from tempfile import NamedTemporaryFile

from intent.scripts.conversion.conll_to_slashtags import conll_to_slashtags
from intent.utils.argutils import require_opt, existsfile
from intent.utils.systematizing import piperunner, ProcessCommunicator
from intent.utils.ConfigFile import ConfigFile
from intent.eval.pos_eval import slashtags_eval
from intent.utils.token import tag_tokenizer, tokenize_string

from intent.utils.env import c, tagger_jar, tagger_model, java_bin

# Logging ----------------------------------------------------------------------
TAG_LOG = logging.getLogger(__name__)

STANFORD_LOG = logging.getLogger('STANFORD_POSTAGGER')

class TaggerError(Exception): pass

class CriticalTaggerError(TaggerError): pass

#===============================================================================
# Set up the stanford tagger to run via stdin.
#===============================================================================

def stanford_stdout_handler(output, queue):
    queue.append(tokenize_string(output, tokenizer=tag_tokenizer))

def stanford_stderr_handler(line):

    if line.startswith('Loading default properties'):
        pass
    elif line.startswith('Reading POS tagger model'):
        pass
    elif line.startswith('done'):
        pass
    elif line.startswith('Type some text to tag,'):
        pass
    elif line.startswith('(For EOF, use Return'):
        pass
    elif line.startswith('Error:'):
        STANFORD_LOG.error(line)
    else:
        STANFORD_LOG.warn(line)


class StanfordPOSTagger(object):
    """
    Instantiate a java VM to run the stanford tagger.
    """
    def __init__(self, model):

        # Get the jar defined in the env.conf file.

        # If the .jar is not defined... ----------------------------------------
        """
        :param model: Path to the model file.
        :type model: str
        """
        if tagger_jar is None:
            TAG_LOG.critical('Path to the stanford tagger .jar file is not defined.')
            raise TaggerError('Path to the stanford tagger .jar file is not defined.')

        self.results_queue = []

        self.st = ProcessCommunicator([java_bin,
                                       '-cp', tagger_jar,
                                       'edu.stanford.nlp.tagger.maxent.MaxentTagger',
                                       '-model', model,
                                       '-sentenceDelimiter', 'newline',
                                       '-tokenize', 'false'],
                                      stderr_func=stanford_stderr_handler,
                                      stdout_func=lambda x: stanford_stdout_handler(x, self.results_queue),
                                      blocking=False)


    def tag_tokenization(self, tokenization, **kwargs):
        return self.tag(tokenization.text(), **kwargs)

    def tag(self, s, **kwargs):

        # Lowercase if asked for
        if kwargs.get('lowercase', True):
            s = s.lower()

        self.st.stdin.write(bytes(s+'\r\n', encoding='utf-8'))

        # Try to flush out to stdin
        try:
            self.st.stdin.flush()
        except BrokenPipeError:
            raise CriticalTaggerError('The Stanford parser unexpectedly quit.')

        while len(self.results_queue) == 0:
            time.sleep(0.25)

        return self.results_queue.pop()

    def close(self):
        self.st.kill()

#===============================================================================
# Functions to call for testing and training.
#===============================================================================

def train_postagger_on_conll(train_file, model_path, delimeter = '/'):
    temp_path = NamedTemporaryFile('w', encoding='utf-8', delete=False)
    temp_path.close()
    conll_to_slashtags([train_file], temp_path.name)
    train_postagger(temp_path.name, model_path, delimeter=delimeter)

def train_postagger(train_file, model_path, delimeter = '/'):
    """
    Given the slashtag file train_file, train a tagger model from it and
    output it to model_path.

    :param train_file: Path to input slashtag file
    :param model_path: Path to output the model
    :param delimeter: Delimeter to separate words/tags
    """

    # If the model path doesn't exists, create it
    dirname = os.path.dirname(model_path)
    if dirname:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

    cmd = '%s -Xmx4096m -cp %s edu.stanford.nlp.tagger.maxent.MaxentTagger -arch generic -model %s -trainFile %s -tagSeparator %s' % (java_bin, tagger_jar, model_path, train_file, delimeter)

    piperunner(cmd, 'stanford_tagger')

    return StanfordPOSTagger(model_path)


def test_postagger(test_file, model_path, out_file, delimeter = '/'):


    """

    :param test_file:
    :param model_path:
    :param out_file:
    :param delimeter:
    """
    # If the folder for the output file doesn't exist, create it.
    dirname = os.path.dirname(out_file)
    if dirname:
        os.makedirs(os.path.dirname(out_file), exist_ok=True)

    cmd = [java_bin, '-Xmx4096m', '-cp', tagger_jar,
           'edu.stanford.nlp.tagger.maxent.MaxentTagger',
           '-arch', 'generic',
           '-model', model_path,
           '-textFile', test_file,
           '-sentenceDelimiter', 'newline',
           '-tokenize', 'false',
           '-tagSeparator', delimeter,
           '-outputFile', out_file]

    STANFORD_LOG.info(' '.join(cmd))

    p = sub.Popen(cmd)
    p.wait()

    #p = ProcessCommunicator(cmd)
    #p.wait()

# Make sure nosetests doesn't think this is a unit test
test_postagger.__test__ = False

def tag(string, model):
    pt = StanfordPOSTagger(tagger_model, tagger_jar)
    return pt.tag(string)


if __name__ == '__main__':

    p = OptionParser()
    p.add_option('-c', '--conf', help='configuration file')
    opts, args = p.parse_args(sys.argv)

    errors = require_opt(opts.conf, "You must specify a configuration file with -c or --conf", True)
    if errors:
        p.print_help()
        sys.exit()

    c = ConfigFile(opts.conf)

    # Set up the log path
    logpath = c.get('log_path')
    log_f = sys.stdout
    if logpath:
        logdir = os.makedirs(os.path.dirname(logpath), exist_ok=True)
        log_f = open(c.get('log_path'), 'w', encoding='utf-8')

    # Now do the testing and training
    train_postagger(c['train_file'],
          c['model'],
          c['delimeter'])
    test(c['test_file'],
         c['model'],
         c['out_file'],
         c['delimeter'])
    time.sleep(1)

    # Evaluate...
    slashtags_eval(c['gold_file'], c['out_file'], c['delimeter'], log_f)

class TestPeriodTagging(unittest.TestCase):
    """

    """

    def runTest(self, result=None):
        p = StanfordPOSTagger(tagger_model)

        first_tagged = p.tag('this is a test . with a period in the middle\n')
        second_tagged= p.tag('and a second . to make sure the feed advances.\n')

        self.assertEqual(len(first_tagged), 11)
        self.assertEqual(len(second_tagged), 10)


