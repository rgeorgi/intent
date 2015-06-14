'''
This module is meant to 
'''
import os

class TagMapException(Exception):
    pass

class TagMap(object):
    '''
    This is a simple class for reading/writing the prototype files used by Haghighi's prototype system.
    '''


    def __init__(self, path):
        # Open the path, this assumes universal mapping
        # one tag pair per line of:
        # FINE   COURSE
        if not path:
            raise TagMapException('Path not specified for tagmap!')

        if not os.path.exists(path):
            raise TagMapException('Tagmap path "%s" does not exist.' % path)

        f = open(path, 'r', encoding='utf-8')

        # mapping
        self.mapping = {}
        for line in f:
            fine, course = line.split()
            self.mapping[fine] = course


    def get(self, original):
        """
        :rtype : str
        """
        return self[original]

    def __getitem__(self, key):
        if key not in self.mapping:
            raise TagMapException('Tag %s not found in mapping.' % key)
        else:
            return self.mapping[key]

    def __contains__(self, item):
        return item in self.mapping

    def __str__(self):
        return str(self.mapping)

    def __nonzero__(self):
        return True


