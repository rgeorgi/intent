'''
Created on Oct 4, 2014

@author: rgeorgi
'''
import xml.sax
import sys
from xigt.codecs import xigtxml
from corpora.IGTCorpus import IGTInstance, IGTCorpus,\
	IGTGlossLangLengthException


if __name__ == '__main__':
	#xigt_h = XigtHandler
	path = '/Users/rgeorgi/Documents/treebanks/xigt-spa.xml'
	
	# Load the xigt corpus instance
	xc = xigtxml.load(open(path, 'r', encoding='utf-8'))
	
	# Initialize an internal corpus.
	c = IGTCorpus()
	
	# Iterate through the instances i
	for igt in xc:
		
		# Initialize an internal IGT instance.
		a = igt.attributes
		
		igt_id = '%s-%s' % (a['doc-id'], igt.id)
				
		l = []
		g = []
		t = []
				
		# Iterate through the tiers
		for tier in igt.tiers:

			# If it's raw data, let's parse it.
			if tier.type == 'odin-raw':
				
				for item in tier:
					tag = item.attributes['tag']
					if tag[0] == 'L':
						l.append(item.content)
					elif tag[0] == 'G':
						g.append(item.content)
					elif tag[0] == 'T':
						t.append(item.content)
						
		# Now, create the instance and append
		# it to the corpus.
		try:
			inst = IGTInstance.from_lines(l, g, t, id=igt_id)
			#print(inst.text())
			c.append(inst)
		except IGTGlossLangLengthException as iglle:
			print(iglle)
			
				
						
			
			
				
			
			