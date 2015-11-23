import os, re
from tempfile import NamedTemporaryFile
from unittest import TestCase

# =============================================================================
# Internal Imports
# =============================================================================
from intent.utils.env import mst_parser, testfile_dir
from intent.utils.systematizing import ProcessCommunicator

# =============================================================================
# Exceptions
# =============================================================================
class MSTParserError(Exception): pass


# =============================================================================
# MST Parser Object
# =============================================================================
class MSTParser(object):
    def __init__(self):
        self.cp = '{}:{}'.format(os.path.join(mst_parser, "./output/classes"),
                                os.path.join(mst_parser, "./lib/trove.jar"))

        self.javaclass = 'mstparser.DependencyParser'
        self.cmd_start = 'java -Xmx1800m -cp {} {} '.format(self.cp, self.javaclass)


    def train(self, train_file, model_file):
        cmd = self.cmd_start + 'train train-file:{} model-name:{}'.format(train_file, model_file)

        p = ProcessCommunicator(cmd, shell=True, stdout_func=print, stderr_func=print)
        exit_code = p.wait()
        return exit_code

    def test(self, model_file, test_file, output_file):
        cmd = self.cmd_start + 'test model-name:{} test-file:{} out-file:{}'.format(model_file, test_file, output_file)
        p = ProcessCommunicator(cmd, shell=True, stdout_func=print, stderr_func=watch_for_java_exception)
        exit_code = p.wait()
        return exit_code

def watch_for_java_exception(string):
    exception_re = re.search('Exception in thread "main" (.*)', string, flags=re.I)
    if exception_re:
        print(string)
    else:
        print(string)


# =============================================================================
# Test Cases
# =============================================================================

class MSTParserTests(TestCase):
    def setUp(self):
        self.train_file = os.path.join(testfile_dir, 'conll/test.conll')
        self.out_file = NamedTemporaryFile('r', delete=False)
        self.model_file = NamedTemporaryFile('r', delete=False)
        self.mp = MSTParser()

    def test_train(self):
        self.assertEqual(0, self.mp.train(self.train_file, self.model_file.name))

    def test_test(self):
        self.mp.train(self.train_file, self.model_file.name)
        self.assertEqual(0, self.mp.test(self.model_file.name, self.train_file, self.out_file.name))

    def tearDown(self):
        self.out_file.close()
        self.model_file.close()
        os.remove(self.model_file.name)
        os.remove(self.out_file.name)

