"""
Created on Apr 4, 2014

@author: rgeorgi
"""
# Built-in imports -------------------------------------------------------------
import os, sys, re
import subprocess as sub
from io import StringIO

# Set up logging
import logging
MAXENT_LOG = logging.getLogger('CLASSIFIER')

# Internal Imports -------------------------------------------------------------
from tempfile import NamedTemporaryFile
from intent.classify.Classification import Classification
from intent.utils.dicts import TwoLevelCountDict
import intent.igt.grams
from intent.utils.systematizing import piperunner, ProcessCommunicator
from intent.utils.token import GoldTagPOSToken
from intent.utils.env import c, mallet, mallet_bin


class ClassifierException(Exception): pass

class EmptyStringException(ClassifierException): pass


class MalletMaxent(object):

    def __init__(self, model):
        self._model = model

        mallet_bin = os.path.join(os.path.join(mallet, 'bin'), 'mallet')

        self.c = sub.Popen([mallet_bin,
                            'classify-file',
                            '--classifier', self._model,
                            '--input', '-',
                            '--output', '-'],
                stdout=sub.PIPE, stdin=sub.PIPE)
        self._first = True

    def info(self):
        """
        Print the feature statistics for the given model. (Assumes MaxEnt)
        """
        mallet = c['mallet']
        info_bin = os.path.join(os.path.join(mallet, 'bin'), 'classifier2info')
        info_p = sub.Popen([info_bin, '--classifier', self._model],
                            stdout=sub.PIPE, stdin=sub.PIPE, stderr=sub.PIPE)

        cur_class = None
        feats = TwoLevelCountDict()

        # Go through and pick out what the features are for
        for line in info_p.stdout:
            content = line.decode(encoding='utf-8')

            class_change = re.search('FEATURES FOR CLASS (.*)', content)
            # Set the current class if the section changes
            if class_change:
                cur_class = class_change.group(1).strip()
                continue

            # Otherwise, let's catalog the features.
            word, prob = content.split()
            feats.add(cur_class, word, float(prob))

        # Now, print some info
        for cur_class in feats.keys():
            print(cur_class, end='\t')
            print('%s:%.4f' % ('<default>', feats[cur_class]['<default>']), end='\t')
            top_10 = feats.top_n(cur_class, n=10, key2_re='^nom')
            print('\t'.join(['%s:%.4f' % (w,p) for w,p in top_10]))

    def classify_string(self, s, **kwargs):
        """
        Run the classifier on a string, breaking it apart as necessary.

        :param s: String to classify
        :type s: str
        """

        token = GoldTagPOSToken(s, goldlabel="NONE")

        sio = StringIO()

        # TODO: Fix the behavior of write_gram such that we can just do it from a string.
        intent.igt.grams.write_gram(token, type='classifier', output=sio, **kwargs)

        c_token = sio.getvalue().strip()
        sio.close()

        result = self.classify(c_token)
        return result

    def classify_token(self, token, **kwargs):

        token = GoldTagPOSToken.fromToken(token, goldlabel='NONE')

        sio = StringIO()
        intent.igt.grams.write_gram(token, type='classifier', output=sio, **kwargs)
        c_token = sio.getvalue().strip()
        sio.close()


        result = self.classify(c_token)

        return result



    def classify(self, string):
        if not string.strip():
            raise EmptyStringException('Empty string passed into classify.')
        else:
            self.c.stdin.write(bytes(string+'\r\n\r\n', encoding='utf-8'))
            self.c.stdin.flush()


            if self._first:
                content = self.c.stdout.readline()
                self._first = False
            else:
                self.c.stdout.readline()
                content = self.c.stdout.readline()

            content = content.decode(encoding='utf-8')

            content = content.split()
            ret_c = Classification(gold=content[0])


            #print(string, content)

            for i in range(1, len(content), 2):

                tag = content[i]

                prob = float(content[i+1])
                ret_c[tag] = float(prob)

            return ret_c


    def close(self):
        self.c.kill()


def train_txt(txt_path, model_path):
    """
    Train a classifier from a svm-light format text file.

    :param txt_path:
    :param model_path:
    """

    vectors = svmlight_to_vectors(txt_path)
    MAXENT_LOG.info("Attempting to train classifier {}".format(model_path))
    p = ProcessCommunicator([mallet_bin, 'train-classifier',
                             '--input', vectors,
                             '--trainer', 'MaxEntTrainer',
                            '--output-classifier', model_path],
                            stdout_func=MAXENT_LOG.info, stderr_func=MAXENT_LOG.info)

    if p.wait() == 0:
        MAXENT_LOG.debug("Success.")
        os.unlink(vectors)
        return MalletMaxent(model_path)
    else:
        raise ClassifierException("Training the classifier did not complete. Check the logs.")

def svmlight_to_vectors(txt):
    """
    Convert a text file to vectors.

    :param txt: Path to the text file.
    """

    MAXENT_LOG.info("Attempting to convert {} to a vector file.".format(txt))

    ntf = NamedTemporaryFile(mode='w', delete=False)
    ntf.close()

    p = ProcessCommunicator('{} import-svmlight --input "{}" --output "{}"'.format(mallet_bin, txt, ntf.name),
                            stdout_func=MAXENT_LOG.info, stderr_func=MAXENT_LOG.warn, shell=True)


    if p.wait() == 0:
        MAXENT_LOG.debug("Successfully created temporary vector file {}".format(ntf.name))
        return ntf.name
    else:
        raise ClassifierException("SVMLight Conversion did not complete successfully.")




if __name__ == '__main__':
    mc = MalletMaxent('/Users/rgeorgi/Dropbox/code/eclipse/dissertation/data/all/xigt_grams.maxent')
    mc.info()