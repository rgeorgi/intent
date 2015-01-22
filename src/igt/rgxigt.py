'''
Subclassing of the xigt package to add a few convenience methods.


'''
import xigt.core
from xigt.core import Metadata, Meta
import sys
import re

#===============================================================================
# Exceptions
#===============================================================================

class RGXigtException(Exception):
	pass

class NoODINRawException(RGXigtException):
	pass 

#===============================================================================


class RGCorpus(xigt.core.XigtCorpus):
	def delUUIDs(self):
		for i in self.igts:
			i.delUUIDs()
			
	def askIgtId(self):
		return 'i%d' % (len(self.igts)+1)
	
	def __len__(self):
		return len(self._list)
	
	

class RGIgt(xigt.core.Igt):

	@classmethod
	def fromXigt(cls, o):
		'''
		Subclass a XIGT object into the child class.
		
		@param cls: The subclass constructor.
		@param o: The original XIGT object.
		'''
		return cls(id=o.id, type=o.type, attributes=o.attributes, metadata=o.metadata, tiers=o.tiers, corpus=o.corpus)

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
	'''
	Subclass of the xigt core "Item."
	'''
	
	def __init__(self, id=None, type=None,
				alignment=None, segmentation=None,
				attributes=None,
				content=None, text=None, tier=None, **kwargs):
		xigt.core.Item.__init__(self, id, type, alignment, content, segmentation, attributes, text, tier)
		
		self.start = kwargs.get('start')
		self.stop = kwargs.get('stop')
		self.index = kwargs.get('index')
		
	@classmethod
	def fromItem(cls, i, start=None, stop=None, index=-1):
		
		if i.segmentation:
			start, stop = [int(s) for s in re.search('\[([0-9]+):([0-9]+)\]', i.segmentation).groups()]
			
		
		return cls(id=i.id, type=i.type, alignment=i.alignment, content=i.content,
					segmentation=i.segmentation, attributes=i.attributes, text=i.text,
					tier=i.tier, index=int(i.attributes.get('index', index)), start=start, stop=stop)
	
	def findUUID(self, uu):
		retlist = []
		if self.attributes.get('uuid') == uu:
			retlist.append(self)
		return retlist
	
	def delUUIDs(self):
		if 'uuid' in self.attributes:
			del self.attributes['uuid']

class RGTier(xigt.core.Tier):
	
	@classmethod
	def fromTier(cls, t):
		
		items = [RGItem.fromItem(i) for i in t.items]
		
		return cls(id=t.id, type=t.type, alignment=t.alignment, content=t.content,
					segmentation=t.segmentation, attributes=t.attributes, metadata=t.metadata,
					items=items, igt=t.igt)

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