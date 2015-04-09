'''
Created on Apr 9, 2015

@author: rgeorgi
'''
from xigt.metadata import Metadata, Meta
from intent.igt.consts import INTENT_GLOSS_MORPH, INTENT_META_TYPE,\
	XIGT_META_TYPE, XIGT_DATA_PROV, INTENT_TOKEN_TYPE
import sys

def set_data_provenance(tier, dp):
	m = Metadata(type=XIGT_META_TYPE)
	dp = Meta(type=XIGT_DATA_PROV, text=dp)
	m.append(dp)
	tier.metadata.append(m)
	
	
def set_gloss_type(tier, token_type):
	'''
	Set the "token type" in metadata.
	
	:param tier: Tier to add the metadata to
	:type tier: Tier
	:param token_type: The type of the token
	:type token_type: str
	'''
	m = Metadata(type=INTENT_META_TYPE)
	token_type = Meta(type=INTENT_TOKEN_TYPE, text=token_type)
	m.append(token_type)
	tier.metadata.append(m)
	
def find_meta(obj, type):
	if obj.metadata is not None:
		for metadata in obj.metadata:
			for meta in metadata.metas:
				if meta.type == type:
					return meta.text
	
def get_gloss_type(tier):
	return find_meta(tier, INTENT_TOKEN_TYPE)
