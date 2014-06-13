'''
Created on Jun 12, 2014

@author: rgeorgi
'''
import argparse
from interfaces.MalletMaxentInfo import MalletMaxentInfo

def get_info(path):
	mmi = MalletMaxentInfo(path)
	mmi.info()

if __name__ == '__main__':
	p = argparse.ArgumentParser()
	p.add_argument('-i', required=True)
	
	args = p.parse_args()
	
	get_info(args.i)