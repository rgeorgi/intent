'''
Created on Oct 15, 2014

@author: rgeorgi
'''
import xigt.core
from xigt.core import Metadata, Meta

class RGCorpus(xigt.core.XigtCorpus):
	def delUUIDs(self):
		for i in self.igts:
			i.delUUIDs()
			
	def askIgtId(self):
		return 'i%d' % (len(self.igts)+1)
	
	def __len__(self):
		return len(self._list)
	
	

class RGIgt(xigt.core.Igt):

	def getTier(self, type):
		return [t for t in self.tiers if t.type == type] 
		
	def findUUID(self, uu):
		retlist = []	
		for t in self.tiers:
			retlist.extend(t.findUUID(uu))
		
		if not retlist:
			return None
		else:
			return retlist[0]
	
	def askTierId(self, type):
		numtiers = len(self.getTier(type))
		return '%s-%s-%d' % (self.id, type, numtiers+1)
	
	def delUUIDs(self):
		if 'uuid' in self.attributes:
			del self.attributes['uuid']
		for t in self.tiers:
			t.delUUIDs()

		
class RGItem(xigt.core.Item):
	
	def findUUID(self, uu):
		retlist = []
		if self.attributes.get('uuid') == uu:
			retlist.append(self)
		return retlist
	
	def delUUIDs(self):
		if 'uuid' in self.attributes:
			del self.attributes['uuid']

class RGTier(xigt.core.Tier):

	def findUUID(self, uu):
		retlist = []
		if self.attributes.get('uuid') == uu:
			retlist.append(self)
		for i in self.items:
			retlist.extend(i.findUUID(uu))
			
		return retlist
	
	def delUUIDs(self):
		if 'uuid' in self.attributes:
			del self.attributes['uuid']
		for i in self.items:
			i.delUUIDs()
	
	def askItemId(self):
		return '%s-%d' % (self.id, self.askIndex())
	
	def askIndex(self):
		return len(self.items)+1
	
class RGMetadata(Metadata):
	pass

class RGMeta(Meta):
	pass