'''
Created on Mar 6, 2014

@author: rgeorgi
'''
import chardet
# 
# def utfread(path):
# 	f = open(path, 'rb')
# 	data = f.read()
# 	f.close()
# 	
# 	encoding = chardet.detect(data)['encoding']
# 	data = data.decode(encoding).encode('utf-8')
# 	return data

def getencoding(path):
	f = open(path, 'rb')
	data = f.read()
	f.close()
	
	return chardet.detect(data)['encoding']
# 	return 'utf-8'