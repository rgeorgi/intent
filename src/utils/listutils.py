'''
Created on Oct 23, 2013

@author: rgeorgi
'''

def all_indices(item, seq):
	return [i for i, x in enumerate(seq) if x == item]

def uniqify (seq, idfun=None): 
	# order preserving
	if idfun is None:
		def idfun(x): return x
	seen = {}
	result = []
	for item in seq:
		marker = idfun(item)
		# in old Python versions:
		# if seen.has_key(marker)
		# but in new ones:
		if marker in seen: continue
		seen[marker] = 1
		result.append(item)
	return result