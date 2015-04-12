from intent.utils.dicts import CountDict

class Classification(CountDict):

    def __init__(self, gold=None):
        CountDict.__init__(self)
        self._gold = gold

    @property
    def gold(self):
        return self._gold
