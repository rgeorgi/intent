'''
Created on Nov 4, 2013

@author: rgeorgi
'''
import unittest
from trees.ptb import parse_ptb_string, parse_ptb_file
from nltk.tree import Tree
from corpus.reader.bracket_parse import BracketParseCorpusReader


class TreeTests(unittest.TestCase):


	def test_282(self):
		t = Tree.parse(tree_282)
# 		
# 	def test_wsj(self):
# 		wsj = '/Users/rgeorgi/Documents/Work/ingestion/LDC95T07'
# 		
# 		print BracketParseCorpusReader(wsj, '.*[0-9][2-9][0-9]{2}.*\.mrg').tagged_sents()[0]
		
	def test_fileparse(self):
		wsj = '/Users/rgeorgi/Documents/Work/ingestion/LDC95T07/RAW/combined/wsj/02/wsj_0200.mrg'
		parse_ptb_file(wsj)

tree_282 = '''( (S 
    (PP-TMP (IN For) 
      (NP (DT a) (NN while) ))
    (PP-TMP (IN in) 
      (NP (DT the) (NNS 1970s) ))
    (NP-SBJ (PRP it) )
    (VP (VBD seemed) 
      (SBAR (-NONE- 0) 
        (S 
          (NP-SBJ (NNP Mr.) (NNP Moon) )
          (VP (VBD was) 
            (PP-PRD (IN on) 
              (NP (DT a) (JJ spending) (NN spree) ))
            (, ,) 
            (PP (IN with) 
              (NP 
                (NP (JJ such) (NNS purchases) )
                (PP (IN as) 
                  (NP 
                    (NP 
                      (NP (DT the) (JJ former) (NNP New) (NNP Yorker) (NNP Hotel) )
                      (CC and) 
                      (NP (PRP$ its) (JJ adjacent) (NNP Manhattan) (NNP Center) ))
                    (: ;) 
                    (NP 
                      (NP (DT a) (JJ fishing\/processing) (NN conglomerate) )
                      (PP (IN with) 
                        (NP 
                          (NP (NNS branches) )
                          (PP-LOC (IN in) 
                            (NP (NNP Alaska) 
                              (, ,)
                              (NNP Massachusetts) 
                              (, ,)
                              (NNP Virginia) 
                              (CC and)
                              (NNP Louisiana) )))))
                    (: ;) 
                    (NP 
                      (NP 
                        (NP (DT a) (JJ former) (NNP Christian) (NNPS Brothers) (NN monastery) )
                        (CC and) 
                        (NP (DT the) (NNP Seagram) (NN family) (NN mansion) ))
                      (PRN 
                        (-LRB- -LRB-)
                        (S-ADV 
                          (NP-SBJ (DT both) )
                          (ADJP-PRD (RB picturesquely) (VBN situated) 
                            (PP-LOC (IN on) 
                              (NP (DT the) (NNP Hudson) (NNP River) ))))
                        (-RRB- -RRB-) ))
                    (: ;) 
                    (NP 
                      (NP (NNS shares) )
                      (PP (IN in) 
                        (NP 
                          (NP (NNS banks) )
                          (PP-LOC 
                            (PP (IN from) 
                              (NP (NNP Washington) ))
                            (PP (TO to) 
                              (NP (NNP Uruguay) ))))))
                    (: ;) 
                    (NP (DT a) (NN motion) (NN picture) (NN production) (NN company) )
                    (, ,) 
                    (CC and)
                    (NP 
                      (NP (NNS newspapers) )
                      (, ,) 
                      (PP (JJ such) (IN as) 
                        (NP 
                          (NP (DT the) (NNP Washington) (NNP Times) )
                          (, ,) 
                          (NP 
                            (NP (DT the) (NNP New) (NNP York) (NNP City) (NNP Tribune) )
                            (PRN 
                              (-LRB- -LRB-)
                              (ADVP-TMP (RB originally) )
                              (NP (DT the) (NNP News) (NNP World) )
                              (-RRB- -RRB-) ))
                          (, ,) 
                          (CC and)
                          (NP (DT the) (JJ successful) (JJ Spanish-language) (NNP Noticias) (FW del) (NNP Mundo) ))))))))))))
    (. .) ))'''



if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()