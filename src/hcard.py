import tornado.httpclient
import services
import logging
import re
import BeautifulSoup
import hcardparser
import urlparse

FEED_RE = re.compile("atom|rss", re.I)
ME_RE = re.compile("^me$|\sme$|\sme\s|^me\s", re.I)

class HCardService(object):
  def getName(self):
    return "hcard"
    
  def lookup(self, handler, identifier, result, user):
    http = tornado.httpclient.AsyncHTTPClient()
    request = tornado.httpclient.HTTPRequest(identifier)
    request.result = result
    request.base = identifier
    request.handler = handler
    http.fetch(request, callback=handler.async_callback(self.onResponse))
      
  def onResponse(self, response):
    if response.code == 200:
      try:
        resObj = {}
        soup = BeautifulSoup.BeautifulSoup(response.body)
        
        logging.error("Parsing %s " % (response.body,))

        # We're going to look for:
        # Feed - any "a" or "link" element with a type of "atom" or "rss"
        feed = soup.findAll( {"a":True, "link":True}, type=FEED_RE)

        logging.error("Feed search: %s" % (feed,))

        for f in feed:
          if f.has_key("href"):
            resObj["urls"] = [{
              "value": urlparse.urljoin(response.request.base, f["href"]),
              "type": "feed" }]

        # rel="me" links
        relMeLinks = soup.findAll("a", rel=ME_RE)

        logging.error("relme search: %s" % (relMeLinks,))

        for link in relMeLinks:
          if not "urls" in resObj: resObj["urls"] = []
          
          resObj["urls"].append( {
            "type": link.string.strip(),
            "value": urlparse.urljoin(response.request.base, link["href"])
          })
          
        # HCard markup
        parser = hcardparser.HCardParser()
        hcardResult = parser.parse_soup(soup)
        if hcardResult:
          self.convertHCard(hcardResult, resObj, response.request.base)

        response.request.result.reportServiceResult(self, resObj)

      except BeautifulSoup.HTMLParseError, e:
        logging.exception(e)
        response.request.result.reportServiceResult(self, None)
        
      except Exception, e:
        logging.exception(e)
        response.request.result.reportServiceResult(self, None)
    else:
      response.request.result.reportServiceResult(self, None)    

  def convertHCard(self, hcard, out, base):
    if "adr" in hcard:
      if not "addresses" in out: out["addresses"] = []

      for adr in hcard["adr"]:
        addr = {};
        if "type" in adr:
          addr["type"] = anAdr["type"]

        if "street-address" in adr: addr["streetAddress"] = adr["street-address"]
        if "extended-address" in adr: addr["extendedAddress"] = adr["extended-address"]
        if "region" in adr: addr["region"] = adr["region"]
        if "postal-code" in adr: addr["postalCode"] = adr["postal-code"]
        if "country-name" in adr: addr["country"] = adr["country-name"]
        if "post-office-box" in adr: addr["postOfficeBox"] = adr["post-office-box"]
        if "locality" in adr: addr["locality"] = adr["locality"]
        if "value" in adr: addr["formatted"] = adr["value"]
        out["addresses"].append(addr)

    if "bio" in hcard:
      out["notes"] = [{"type":"bio", "value":hcard["bio"]}]

    if "bday" in hcard:
      out["bday"] = hcard["bday"]

    if "category" in hcard:
      out["category"] = hcard["category"]

    if "email" in hcard:
      if not "emails" in out: out["emails"] = [];

      for anEmail in hcard["email"]:
        email = {}

        if "type" in anEmail: email["type"] = anEmail["type"][0]
        else: email["type"] = "email"
        
        if "values" in anEmail: email["value"] = anEmail["values"][0] # TODO handle repeated values
        elif "value" in anEmail: email["value"] = anEmail["value"]
        out["emails"].append(email)

    if "fn" in hcard:
      out["displayName"] = hcard["fn"]

    if "geo" in hcard:
      pass # TODO support geo

    if "key" in hcard:
      if not "publicKeys" in out: out["publicKeys"] = [];
      for aKey in hcard["key"]:
        out["publicKeys"].append(aKey)

    if "n" in hcard:
      if not "name" in out: out["name"] = {}

      if "given-name" in hcard["n"]: out["name"]["givenName"] = hcard["n"]["given-name"]
      if "additional-name" in hcard["n"]: out["name"]["additional"] = hcard["n"]["additional-name"]
      if "family-name" in hcard["n"]: out["name"]["familyName"] = hcard["n"]["family-name"]

    if "org" in hcard:
      for o in hcard["org"]:
        if not "organizations" in out: out["organizations"] = []

        org = {"name":o["organization-name"]}
        if "organization-unit" in o: org["department"] = o["organization-unit"]

        out["organizations"].append(org)
    # TODO what about title?
        
    if "photo" in hcard:
      if not "photos" in out: out["photos"] = []
      for aPhoto in hcard["photo"]:
        out["photos"].append( {"type":"profile", "value": urlparse.urljoin(base, aPhoto)} )

    if "tel" in hcard:
      for aTel in hcard["tel"]:
        tel = {};
        if "type" in aTel: tel["type"] = aTel["type"];
        else: tel["type"] = "phone"

        if "value" in aTel: tel["value"] = aTel["value"]

        if not "phoneNumbers" in out: out["phoneNumbers"] = []
        out["phoneNumbers"].append(tel)


services.Factory.registerService(HCardService())




