'''
Created on Aug 26, 2013

@author: rgeorgi
'''
import sys, re, unittest
from collections import defaultdict, Callable, OrderedDict


class CountDict(object):
    def __init__(self):
        self._dict = defaultdict(int)

    def add(self, key, value=1):
        self[key] += value

    def __str__(self):
        return self._dict.__str__()

    def __repr__(self):
        return self._dict.__repr__()

    def total(self):
        values = self._dict.values()
        total = 0
        for v in values:
            total += v
        return total

    #===========================================================================
    #  Stuff that should be inheritable
    #===========================================================================

    def __getitem__(self, k):
        return self._dict.__getitem__(k)

    def __setitem__(self, k, v):
        self._dict.__setitem__(k, v)

    def __contains__(self, k):
        return self._dict.__contains__(k)

    def __len__(self):
        return self._dict.__len__()

    def __delitem__(self, k):
        self._dict.__delitem__(k)

    def keys(self):
        return self._dict.keys()

    def items(self):
        return self._dict.items()

    #  -----------------------------------------------------------------------------

    def largest(self):
        return sorted(self.items(), reverse=True, key=lambda k: k[1])[0]

    def most_frequent(self, minimum = 0, num = 1):
        '''
        Return the @num entries with the highest counts that
        also have at least @minimum occurrences.

        @param minimum: int
        @param num: int
        '''
        items = list(self.items())
        items.sort(key = lambda item: item[1], reverse=True)
        ret_items = []
        for item in items:
            if item[1] > minimum:
                ret_items.append(item[0])
            if num and len(ret_items) == num:
                break

        return ret_items

    def most_frequent_count(self, minimum = 0, num = 1):
        most_frequent_keys = self.most_frequent(minimum, num)
        most_frequent_values = map(lambda key: self[key], most_frequent_keys)
        return most_frequent_values

class DefaultOrderedDict(OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
           not isinstance(default_factory, Callable)):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                               OrderedDict.__repr__(self))

class TwoLevelCountDict(object):
    def __init__(self):
        self._dict = defaultdict(CountDict)

    def add(self, key_a, key_b, value=1):
        self[key_a][key_b] += value

    def top_n(self, key, n=1, min_num = 1, key2_re = None):
        s = sorted(self[key].items(), reverse=True, key=lambda x: x[1])
        if key2_re:
            s = [i for i in s if re.search(key2_re, i[0])]

        return s[0:n]


    def most_frequent(self, key, num = 1, key2_re = ''):
        most_frequent = None
        biggest_count = 0

        for key2 in self[key].keys():

            # The key2_re is used to ignore certain keys
            if key2_re and re.search(key2_re, key2):
                continue

            else:
                count = self[key][key2]
                if count > biggest_count and count >= num:
                    most_frequent = key2
                    biggest_count = count

        return most_frequent






    def fulltotal(self):
        total = 0
        for key in self.keys():
            total += self.total(key)
        return total

    def total(self, key):
        count = 0
        for key2 in self[key].keys():
            count += self[key][key2]
        return count


    def distribution(self, key, use_keys=[], add_n = 0):
        dist_set = set([])

        if not use_keys:
            use_keys = self[key].keys()

        total = 0
        for key2 in use_keys:
            total += self[key][key2] + add_n

        for key2 in use_keys:
            dist_set.add((key2, (self[key][key2]+add_n) / float(total)))


        return dist_set

    #===========================================================================
    # Stuff that should've been inherited
    #===========================================================================

    def __str__(self):
        return self._dict.__str__()

    def __getitem__(self, k):
        return self._dict.__getitem__(k)

    def __setitem__(self, k, v):
        self._dict.__setitem__(k, v)

    def __contains__(self, k):
        return self._dict.__contains__(k)

    def keys(self):
        return self._dict.keys()

    def __len__(self):
        return self._dict.__len__()

#===============================================================================
# 
#===============================================================================
class POSEvalDict(TwoLevelCountDict):

    def __init__(self):
        TwoLevelCountDict.__init__(self)
        self.mapping = {}


    def keys(self):
        return [str(k) for k in TwoLevelCountDict.keys(self)]

    def _resetmapping(self):
        self.mapping = {t:t for t in self.keys()}

    def _mapping(self):
        if not self.mapping:
            self._resetmapping()

    def map(self, k):
        return self.mapping[k]

    def unmap(self, k):
        keys = [o for o, n in self.mapping.items() if n == k]
        assert len(keys) == 1
        return keys[0]

    def overall_breakdown(self, title=None):
        ret_s = ''
        if title:
            ret_s = title+','

        ret_s += 'accuracy, matches, total\n'
        ret_s += '%.2f,%s,%s\n' % (self.accuracy(), self.all_matches(), self.fulltotal())
        return ret_s



    def breakdown_csv(self):
        ret_s = 'TAG,PRECISION,RECALL,F_1,IN_GOLD,IN_EVAL,MATCHES\n'

        for label in self.keys():
            ret_s += '%s,%.2f,%.2f,%.2f,%d,%d,%d\n' % (label,
                                                       self.tag_precision(label),
                                                       self.tag_recall(label),
                                                       self.tag_fmeasure(label),
                                                       self.total(label),
                                                       self.col_total(label),
                                                       self.matches(label))
        return ret_s

    def tag_recall(self, t):
        total = self.total(t)
        return float(self.matches(t)) / total * 100 if total != 0 else 0

    def matches(self, t):
        self._mapping()
        return self[self.mapping[t]][t]

    def all_matches(self):
        self._mapping()

        matches = 0
        for t in self.keys():
            matches += self.matches(t)
        return matches

    def accuracy(self):
        totals = self.fulltotal()
        matches = self.all_matches()
        #print('%d/%d' % (matches, totals))

        return float(matches / totals) * 100 if totals != 0 else 0

    def col_total(self, tag_a):
        self._mapping()

        totals = 0
        for tag_b in self.keys():
            totals += self[tag_b][tag_a]
        return totals

    def tag_fmeasure(self, tag):
        p = self.tag_precision(tag)
        r = self.tag_recall(tag)

        return 2 * (p*r)/(p+r) if (p+r) != 0 else 0


    def tag_precision(self, tag_a):
        '''
        Calculate the precision for a given tag

        @param tag_a: the tag to precision for.
        '''
        self._mapping()

        tag_total = self.col_total(tag_a)
        return (float(self.matches(tag_a)) / tag_total * 100) if tag_total != 0 else 0


    def greedy_n_to_1(self):
        '''
        Remap the tags in such a way to maximize matches. In this mapping,
        multiple output tags can map to the same gold tag.
        '''

        self._mapping()

        for orig_tag in self.keys():
            most_matches = 0
            best_alt = orig_tag

            # Iterate through every alternate
            # and see if remapping fares better.
            for alt_tag in self.keys():

                if self[alt_tag][orig_tag] > most_matches:
                    most_matches = self[alt_tag][orig_tag]
                    best_alt = alt_tag

            self.mapping[orig_tag] = best_alt

        return self.mapping


    def greedy_1_to_1(self, debug=False):
        '''
        Remap the tags one-to-one in such a way as to maximize matches.

        This will be similar to bubble sort. Start off with 1:1. Then, go
        through each pair of tags and try swapping the two. If we get a net
        gain of matches, then keep the swap, otherwise don't. Repeat until we
        get a full run of no swaps.
        '''
        self._mapping()
        mapping = self.mapping

        while True:


            # 2) Now, for each tag, consider swapping it with another tag, and see if
            #    we improve.
            improved = False

            for orig_tag, cur_tag in sorted(mapping.items()):

                cur_matches = self[orig_tag][cur_tag]
                best_alt = cur_tag
                swapped = False
                best_delta = 0

                for alt_tag in sorted(self.keys()):

                    # alt_tag -- is the tag we are considering swapping
                    #            the mapping for orig_tag to.

                    # cur_tag -- is the tag that orig_tag is currently
                    #            mapped to.

                    # alt_parent_tag -- the tag that previously was
                    #                   assigned to alt_tag
                    alt_parent_tag = self.unmap(alt_tag)


                    # When looking up the possible matches, remember
                    # that the first bracket will be the original tag
                    # and the second tag will be what it is mapped to.

                    # B MATCHES ------------------------------------------------

                    matches_b_old = self[alt_tag][alt_parent_tag]

                    # And the matches that we will see if swapped...
                    matches_b_new = self[cur_tag][alt_parent_tag]


                    # A MATCHES ------------------------------------------------

                    # Now, the matches that we will gain by the swap....
                    matches_a_new = self[alt_tag][orig_tag]

                    # And where we last were with relationship to the mapping...
                    matches_a_old = self[cur_tag][orig_tag]


                    matches_delta = (matches_b_new - matches_b_old) + (matches_a_new - matches_a_old)

                    if matches_delta > 0:
                        best_delta = matches_delta
                        best_alt = alt_tag
                        swapped = True

                # If we have found a better swap...
                if swapped:

                    new_alt = mapping[orig_tag]
                    mapping[self.unmap(best_alt)] = new_alt
                    mapping[orig_tag] = best_alt
                    improved = True
                    self.mapping = mapping
                    break

            # Break out of the while loop
            # if we have not made a swap.
            if not improved:
                break



        self.mapping = mapping



    #===========================================================================
    def error_matrix(self, csv=False, ansi=False):
        '''
        Print an error matrix with the columns being the tags assigned by the
        system and the rows being the gold standard answers.
        '''

        self._mapping()



        cellwidth = 12
        if not csv:
            cell = '%%-%ds' % cellwidth
        else:
            cell='%s,'

        keys = sorted(self.keys())

        # Print header
        header_start = int((len(keys)*cellwidth)/2)-8

        if not csv:
            ret_s = ' '*header_start + '[PREDICTED ALONG TOP]' + '\n'
        else:
            ret_s = ''


        ret_s += cell % ''

        # Print the column labels
        for key in keys:
            if self.mapping[key] != key:
                ret_s += cell % ('%s(%s)' % (key, self.mapping[key]))
            else:
                ret_s += cell % key

        # Add a total and a recall column.
        ret_s += '| ' if not csv else ''

        ret_s += (cell % 'TOT') + (cell % 'REC')

        # Next Line
        ret_s += '\n'


        #=======================================================================
        # Now, print all the middle of the cells
        #=======================================================================
        for key_b in keys:
            ret_s += cell % key_b
            rowtotal = 0
            for key_a in keys:

                # Make it bold
                if self.mapping[key_a] == key_b:
                    if ansi:
                        ret_s += '\033[94m'

                count = self[key_b][key_a]
                rowtotal += count

                ret_s += cell % count

                # Unbold it...
                if self.mapping[key_a] == key_b:
                    if ansi:
                        ret_s += '\033[0m'

            # Add the total for this row...
            ret_s += '| ' if not csv else ''
            ret_s += cell % rowtotal

            # And calc the recall
            if rowtotal == 0:
                ret_s += cell % ('%.2f' % 0)
            else:
                ret_s += cell % ('%.2f' % (float(self[key_b][self.mapping[key_b]]) / rowtotal*100))

            ret_s += '\n'

        #===================================================================
        # Finally, print all the stuff at the bottom
        #===================================================================

        # 1) Print a separator line at the bottom.
        #ret_s += cell % ''   # ( Skip a cell )
        if not csv:
            for i in range(len(keys)+1):
                ret_s += cell % ('-'*cellwidth)
            ret_s += '\n'

        # 2) Print the totals for each column
        ret_s += cell % 'TOT'
        for key_a in keys:
            ret_s += cell % (self.col_total(key_a))
        ret_s += '\n'

        # 3) Print the precision for each column.
        ret_s += cell % 'PREC'
        for key_a in keys:
            ret_s += cell % ('%.2f' % self.tag_precision(key_a))

        return ret_s+'\n'

class MatrixTest(unittest.TestCase):
    def runTest(self):
        ped = POSEvalDict()
        ped.add('A','A',1)
        ped.add('A','B',2)
        ped.add('A','C',4)
        ped.add('B','A',3)
        ped.add('B','B',1)
        ped.add('C','A',1)

#		A	   B	   C	   | TOT	 REC	 
# A		1	   2	   4	   | 7	   14.29   
# B		3	   1	   0	   | 4	   25.00   
# C		1	   0	   0	   | 1	   0.00	
#	--------------------------------
# TOT	5 	   3	   4	   
# PREC	20.00  33.33   0.00	'''

        self.assertEqual(ped.tag_precision('A'), float(1)/5*100)
        self.assertEqual(ped.tag_recall('A'), float(1)/7*100)
        self.assertEqual(ped.tag_recall('C'), 0)
        self.assertEqual(ped['A']['C'], 4)

class GreedyTest(unittest.TestCase):

    def runTest(self):
        ped = POSEvalDict()
        ped.add('A','B',5)
        ped.add('A','C',2)
        ped.add('B','A',10)
        ped.add('C','C',10)

# 		A	   B	   C	   | TOT	 REC	 
# A	   0	   5	   0	   | 5	   0.00	
# B	   10	   0	   0	   | 10	   0.00	
# C	   0	   0	   10	   | 10	   100.00  
# --------------------------------
# TOT	10	  	5	   		10	  
# PREC	0.00	0.00	100.00  

        ped.greedy_1_to_1()
        print(ped.error_matrix(True))


class StatDict(defaultdict):
    '''

    '''

    def __init__(self, type=int):
        '''
        Constructor
        '''
        defaultdict.__init__(self, type)

    @property
    def total(self):
        return sum(self.values())

    @property
    def distribution(self):
        return {(k,float(v)/self.total) for k, v in self.items()}

    @property
    def counts(self):
        return set(self.items())