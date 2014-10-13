'''
Created on Oct 2, 2014

@author: rgeorgi
'''
from argparse import ArgumentParser
from utils.argutils import existsfile, ArgPasser
from ingestion.eci.eci import ECITextParser
from utils.ConfigFile import ConfigFile

if __name__ == '__main__':
	p = ArgumentParser()
	p.add_argument('-c', '--config', help='Config file path', type=existsfile, required=True)
	
	args = p.parse_args()
	
	c = ConfigFile(args.config)
	
	ep = ECITextParser()
	ep.parse(**c)