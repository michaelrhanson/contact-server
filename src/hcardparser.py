# Based on
# https://pydataportability.googlecode.com/svn/buildouts/microformats
#
#    Author: Christian Scholz <cs at comlounge net>
#    Home Page: http://mrtopf.de/blog
#    Keywords: microformats parser hcard vcard dataportability
#    License: LGPL
#    DOAP record: pydataportability.microformats.hcard-0.1dev-r25.xml
import logging
import re
import doctest
import BeautifulSoup

VCARD_RE = re.compile("^vcard$|\svcard$|^vcard\s|\svcard\s", re.I)

FIELDS = ['fn','nickname','n','org','sort-string','url','adr','email','label','tel','geo','photo','bday',
          'logo','sound','title','role','category','note','class','key','mailer','uid','rev']

ADR_FIELDS = ['post-office-box', 'extended-address', 'street-address', 'locality', 'region',
          'postal-code', 'country-name', 'type', 'value']

N_FIELDS = ['family-name', 'given-name', 'additional-name', 'honorific-prefix', 'honorific-suffix']

ORG_FIELDS = ['organization-name', 'organization-unit']

TEL_FIELDS = ['type', 'value']

class HCardParser(object):
  """parses HCards
  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo class='vcard'>  <div class='fn'>Hi</div> </foo>"))
  {'fn': u'Hi'}

  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo class='vcard'><div class='adr'><span class='post-office-box'>Box 15</span>, <span class='locality'>Anytown</span></foo>"))
  {'adr': [{'post-office-box': u'Box 15', 'locality': u'Anytown'}]}

  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo class='vcard'><div class='adr'><span class='post-office-box'>Box 15</span>, <span class='locality'>Anytown</span></div><div class='adr'><span class='post-office-box'>Box 18</span>, <span class='locality'>Othertown</span></div></foo>"))
  {'adr': [{'post-office-box': u'Box 15', 'locality': u'Anytown'}, {'post-office-box': u'Box 18', 'locality': u'Othertown'}]}

  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo></foo>"))

  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo class='vcard'><div class='email'>test@test.com</div></foo>"))
  {'email': u'test@test.com'}

  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo class='vcard'><a class='email' href='mailto:test@test.com'>mail me</div></foo>"))
  {'email': u'test@test.com'}

  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo class='vcard'><div class='n'><span class='given-name'>Joe</span><span class='family-name'>Doe</span>"))
  {'n': {'given-name': u'Joe', 'family-name': u'Doe'}}

  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo class='vcard'><div class='org'>Miskatonix</div>"))
  {'org': [{'organization-name': u'Miskatonix'}]}

  >>> HCardParser().parse_soup(BeautifulSoup.BeautifulSoup("<foo class='vcard'><div class='org'><div class='organization-name'>Miskatonix</div><div class='organization-unit'>Phlogistonic Impeller Branch</div></div>"))
  {'org': [{'organization-unit': u'Phlogistonic Impeller Branch', 'organization-name': u'Miskatonix'}]}


  """
  
  
  def checkNode(self,node):
    """check a node if some microformat might be inside"""
    if node.has_key("class"):
      return (node["class"].search(VCARD_RE) != None)
    return False
  
  def parse_soup(self, soup):
    node = soup.contents[0]
    
    self.vcard = None
    while node:
      if node.__class__ != BeautifulSoup.Tag: 
        node = node.next
        continue
      
      if node.has_key("class"):
        # Begin a vcard?
        if VCARD_RE.search(node["class"]) != None:
          if self.vcard: # vcard inside vcard: skip entire subtree
            node = node.nextSibling
            continue
          else:
            self.vcard = {}
        
        # Process a field?
        classes = [c.lower() for c in node["class"].split()]
        for field in FIELDS:
          if field in classes:
            method = getattr(self, "handle_%s" % field, self.handlefield)
            method(field, node)

      node = node.next
    return self.vcard

  def handlefield(self,field,node):
      """generic field handler"""
      self.vcard[field]=node.string
      
  def handle_photo(self,field,node):
      """for photos we use the URL in the href if one is present, else the src"""
      if not "photo" in self.vcard:
        self.vcard["photo"] = []
        
      if node.has_key("href"):
        self.vcard['photo'].append(node["href"])
      elif node.has_key("src"):
        self.vcard['photo'].append(node["src"])

  def handle_url(self,field,node):
      """extract the URL"""
      if node.has_key("href"):
        self.vcard['url'] = node["href"]

  def handle_email(self,field,node):
      """extract the email address"""

      if node.has_key("href"):
        url = node["href"].lower()
        if url.startswith('mailto:'):
            self.vcard['email'] = url[7:]
      else:
        self.vcard['email'] = node.string
      
  def handle_org(self, field, node):
    if not 'org' in self.vcard: self.vcard['org'] = []
    org = {}
    self.vcard['org'].append(org)

    for inode in node.contents:
      if not inode.__class__ == BeautifulSoup.Tag: continue
      if inode.has_key("class"):
        classes = [c.lower() for c in inode["class"].split()]
        for field in ORG_FIELDS:
          if field in classes:
            org[field] = inode.string
    
    if not "organization-name" in org:
      org["organization-name"] = node.string
      

  def handle_adr(self, field, node):
    if not 'adr' in self.vcard: self.vcard['adr'] = []
    adr = {}
    self.vcard['adr'].append(adr)

    any = False
    for inode in node.contents:
      if not inode.__class__ == BeautifulSoup.Tag: continue
      if inode.has_key("class"):
        classes = [c.lower() for c in inode["class"].split()]
        for field in ADR_FIELDS:
          if field in classes:
            adr[field] = inode.string.strip()
            any = True
    if not any:
      adr["value"] = node.string
    

  def handle_tel(self, field, node):
    if not 'tel' in self.vcard: self.vcard['tel'] = []
    tel = {}
    self.vcard['tel'].append(tel)

    for inode in node.contents:
      if not inode.__class__ == BeautifulSoup.Tag: continue
      if inode.has_key("class"):
        classes = [c.lower() for c in inode["class"].split()]
        for field in TEL_FIELDS:
          if field in classes:
            adr[field] = inode.string
    if not "value" in tel:
      tel["value"] = node.string

  def handle_n(self, field, node):
    self.vcard['n'] = {}
    for inode in node.contents:
      if not inode.__class__ == BeautifulSoup.Tag: continue
      if inode.has_key("class"):
        classes = [c.lower() for c in inode["class"].split()]
        for field in N_FIELDS:
          if field in classes:
            self.vcard['n'][field] = inode.string


if __name__ == "__main__":
    import doctest
    doctest.testmod()