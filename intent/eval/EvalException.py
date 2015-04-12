'''
Created on Mar 3, 2014

@author: rgeorgi
'''

class EvalException(Exception):
    '''
    classdocs
    '''


    def __init__(self, msg):
        '''
        Constructor
        '''
        self.message = msg

class POSEvalException(Exception):

    def __init__(self, msg):
        Exception.__init__(self, msg)
