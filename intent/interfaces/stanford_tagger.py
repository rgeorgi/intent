'''
Created on Oct 22, 2013

@author: rgeorgi
'''

import os, sys, re, unittest, time, logging
import subprocess as sub
from optparse import OptionParser

# Internal Imports -------------------------------------------------------------
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
    '''
    Instantiate a java VM to run the stanford tagger.
    '''
    def __init__(self, model):

        # Get the jar defined in the env.conf file.

        # If the .jar is not defined... ----------------------------------------
        if tagger_jar is None:
            TAG_LOG.critical('Path to the stanford tagger .jar file is not defined.')
            raise TaggerError('Path to the stanford tagger .jar file is not defined.')

        self.st = ProcessCommunicator([java_bin,
                                       '-cp', tagger_jar,
                                       'edu.stanford.nlp.tagger.maxent.MaxentTagger',
                                       '-model', model,
                                       '-sentenceDelimiter', 'newline',
                                       '-tokenize', 'false'], stderr_func=stanford_stderr_handler)


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

        #=======================================================================
        # Have a sliding window here such that we find all the tokens...
        #=======================================================================
        word_count = 0
        input_len = len(s.split())

        # We are now using a version of the stanford tagger which finally respects
        # the sentence_delimiter argument. So we only need one readline() for the sentence.
        output_str = self.st.stdout.readline().decode('utf-8', errors='replace')



        return tokenize_string(output_str, tokenizer=tag_tokenizer)

    def close(self):
        self.st.kill()

#===============================================================================
# Functions to call for testing and training.
#===============================================================================

def train(train_file, model_path, delimeter = '/'):
    # Exists
    existsfile(train_file)

    # If the model path doesn't exists, create it
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    cmd = '%s -Xmx4096m -cp %s edu.stanford.nlp.tagger.maxent.MaxentTagger -arch generic -model %s -trainFile %s -tagSeparator %s' % (java_bin, tagger_jar, model_path, train_file, delimeter)

    piperunner(cmd, 'stanford_tagger')

def eval(test_file, model_path, delimeter = '/'):
    global stanford_jar
    cmd = '%s -Xmx4096m -cp %s edu.stanford.nlp.tagger.maxent.MaxentTagger -arch generic -model %s -textFile %s -sentenceDelimiter newline -tokenize false -tagSeparator %s' % (java_bin, stanford_jar, model_path, test_file, delimeter )
    piperunner(cmd, 'stanford_tagger')


def test(test_file, model_path, out_file, delimeter = '/'):
    global stanford_jar

    existsfile(test_file)
    existsfile(model_path)

    # If the folder for the output file doesn't exist, create it.
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    cmd = '%s -Xmx4096m -cp %s edu.stanford.nlp.tagger.maxent.MaxentTagger -arch generic -model %s -textFile %s -sentenceDelimiter newline -tokenize false -tagSeparator %s -outputFormat slashTags -outputFile %s' % (java_bin, stanford_jar, model_path, test_file, delimeter, out_file)
    piperunner(cmd, 'stanford_tagger')

# Make sure nosetests doesn't think this is a unit test
test.__test__ = False

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
    train(c['train_file'],
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


