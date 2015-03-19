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
	return [node for node in element.childNodes if node.localName == tag]

def getIntAttr(element, tag):
	attr = element.getAttribute(tag)
	if attr:
		return int(attr)
	else:
		return None

def get_ref(element, tag):
	return element.getAttribute(tag)[13:-1]

def find_tag(element, tag, max_depth = 0, depth = 0):
	if not element.hasChildNodes() or max_depth and depth > max_depth:
		return []
	else:
		nodes = []
		for childnode in element.childNodes:
			if re.search(tag, str(childnode.localName)):
				nodes.append(childnode)
			nodes += find_tag(childnode, tag, max_depth=max_depth, depth=depth+1)
		return nodes
