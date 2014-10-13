'''
Created on Mar 17, 2014

@author: rgeorgi
'''

from xigt.codecs import xigtxml
from corpora.IGTCorpus import IGTCorpus, IGTInstance, IGTTier
from multiprocessing import Pool

from xml.sax.xmlreader import XMLReader
from xml.sax import ContentHandler

def process_instance(xigt_inst, corpus):
	
	cleaned = [t for t in xigt_inst.tiers if t.type == 'odin-clean']

	for clean_tier in cleaned:
		glosses = [g.content for g in clean_tier.items if g.attributes['tag'] == 'G' and g.content]
		trans = [t.content for t in clean_tier.items if t.attributes['tag'] == 'T' and t.content]
		lang = [l.content for l in clean_tier.items if l.attributes['tag'] == 'L' and l.content]
		
		if glosses and trans and lang:			
			
			i = IGTInstance(id=xigt_inst.id)
			
			
			l = IGTTier.fromString(lang[0], kind='lang')
			g = IGTTier.fromString(glosses[0], kind='gloss')
			t = IGTTier.fromString(trans[0], kind='trans')

			i.append(l)
			i.append(g)
			i.append(t)
			
			corpus.append(i)

#===============================================================================
# Make XIGT SAX Parser
#===============================================================================

class XigtHandler(ContentHandler):
	
	def __init__(self):
		ContentHandler.__init__(self)		
	
	def startElement(self, name, attrs):
		if name == 'igt':
			# Initialize new IGT Instance
			self.curInst = IGTInstance(id='%s-%s' % (attrs['doc-id'],attrs['id']))
			
		ContentHandler.startElement(self, name, attrs)
		
		

# class XigtParser(object):
# 	'''
# 	classdocs
# 	'''
# 
# 
# 	def __init__(self):
# 		'''
# 		Constructor
# 		'''
# 		self._corpus = IGTCorpus()
# 		
# 	@property
# 	def corpus(self):
# 		return self._corpus
# 	
# 	
# 	
# 	def parse_file(self, path):
# 		xigt_corpus = xigtxml.load(path)
# 		pool = Pool(processes=4)
# 		for inst in xigt_corpus.igts:
# 			process_instance(inst, self.corpus)
# 
# 		

		
			
					
			