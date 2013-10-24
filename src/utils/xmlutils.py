'''
Created on Oct 23, 2013

@author: rgeorgi
'''
import re
import xml.dom.minidom


def toxml(e):
	xml_str = e.toxml().replace('\n', '')
	xml_str = re.sub('>[^<\S]+<', '><', xml_str)
	elements = re.findall('<[^>]+>(?:[^<]+<[^>]+>)?', xml_str)
	ret_str = ''
	tabs = 0
	for element in elements:
		
		if element.startswith('</'):		
			tabs -= 1
			ret_str += '\t'*tabs+element+'\n'
		elif element.endswith('/>') or re.search('<[^>]+>[^<]+', element) or element.startswith('<?'):
			ret_str += '\t'*tabs+element+'\n'
		else:
			ret_str += '\t'*tabs+element+'\n'
			tabs += 1
			
	return ret_str.encode('utf-8', 'xmlcharrefreplace')

def createTextNode(content):
	impl = xml.dom.minidom.getDOMImplementation()
	doc = impl.createDocument(None, 'none', None)
	return doc.createTextNode(content)

def get_child_tags(element, tag):
	return filter(lambda node: node.localName == tag, element.childNodes)