'''
Created on Aug 31, 2013

@author: rgeorgi
'''
import optparse, sys, os, re

if __name__ == '__main__':
	p = optparse.OptionParser()
	p.add_option('-c', '--conf', help='Configuration file.')