import xml.dom.minidom

def read(xmlstring):
  doc = xml.dom.minidom.parseString(xmlstring)
  remove_whilespace_nodes(doc.documentElement)
  return elementtodict(doc.documentElement)

def elementtodict(parent):
  child = parent.firstChild
  if parent.attributes and parent.attributes.length > 0:
    pass
  elif (not child):
    return None
  elif (child.nodeType == xml.dom.minidom.Node.TEXT_NODE):
    return child.nodeValue
	
  d={}
  for i in xrange(parent.attributes.length):
    attr = parent.attributes.item(i)
    d["@%s" % attr.name] = attr.value

  while child is not None:
    if (child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE):
      try:
        d[child.tagName]
      except KeyError:
        d[child.tagName]=[]
      d[child.tagName].append(elementtodict(child))
    elif (child.nodeType == xml.dom.minidom.Node.TEXT_NODE):
      d["text()"] = child.nodeValue
      
    child = child.nextSibling    
  return d

def remove_whilespace_nodes(node, unlink=True):
  remove_list = []
  for child in node.childNodes:
    if child.nodeType == xml.dom.Node.TEXT_NODE and not child.data.strip():
      remove_list.append(child)
    elif child.hasChildNodes():
      remove_whilespace_nodes(child, unlink)
  for node in remove_list:
    node.parentNode.removeChild(node)
    if unlink:
      node.unlink()
      
      
