import tornado.httpclient
import services
import json
import logging
import urlparse
import xml.dom.minidom

TEMPLATE_CACHE = {}

REL_DICTIONARY = {
  'http://portablecontacts.net/spec/1.0':'data',      # Poco data treated specially, maybe?
  'http://webfinger.net/rel/profile-page':'profile',  # Sure
  'http://microformats.org/profile/hcard':'profile',  # Yep
  'http://gmpg.org/xfn/11':'profile',                 # Hrm.. really?
  'http://specs.openid.net/auth/2.0/provider':'data', # Moderately useful
  'describedby':'profile',                            # Sounds good
  # describedby/@type=application/rdf+xml             # Um... maybe?
  'http://schemas.google.com/g/2010#updates-from':'updates' #  type='application/atom+xml'
};


class WebfingerService(object):
  def getName(self):
    return "webfinger"
    
  def lookup(self, handler, identifier, result, user):

    if identifier.find("http:") == 0 or identifier.find("https:") == 0:
      result.reportServiceResult(self, None)
      return
      
    split = identifier.split("@", 2);
    if len(split) == 2 and len(split[0]) > 0 and len(split[1]) > 0:
      domain = split[1]
      userid = split[0]
    else:
      result.reportServiceResult(self, None)
      return
      
    try:
      key = domain
      logging.error("got key %s" % key)
      if key in TEMPLATE_CACHE:
        if TEMPLATE_CACHE[key]:
          self.onTemplate(result, handler, userid, domain, TEMPLATE_CACHE[key])
        else:
          result.reportServiceResult(self, None)
      else:
        logging.error("No key hit")
        http = tornado.httpclient.AsyncHTTPClient()
        hostMetaRequest = tornado.httpclient.HTTPRequest("http://%s/.well-known/host-meta" % (key,)) # TODO require HTTPS?
        hostMetaRequest.result = result
        hostMetaRequest.key = key
        hostMetaRequest.handler = handler
        hostMetaRequest.domain = domain
        hostMetaRequest.userid = userid
        logging.error("requesting %s" % ("%s/.well-known/host-meta" % (key,),))
        http.fetch(hostMetaRequest, callback=handler.async_callback(self.onHostMetaResponse))
      
    except Exception, e:
      logging.error(e)
      result.reportServiceResult(self, None)

  def onHostMetaResponse(self, response):
    if response.code == 200:
      try:
        logging.debug("Got hostmeta: %s" % response.body)
        dom = xml.dom.minidom.parseString(response.body)
        # hosts = dom.getElementsByTagName("Host") TODO check Host value?
        links = dom.getElementsByTagName("Link")

        template = None
        for link in links:
          logging.error("Found link - %s" % link.getAttribute("rel"))
          if link.getAttribute("rel") == "lrdd":
            template = link.getAttribute("template")
            if len(template):
              break
            else: template = None
        
        if template:
          TEMPLATE_CACHE[response.request.key] = template
          logging.error("Found template %s" % template)
          self.onTemplate(response.request.result, response.request.handler, response.request.userid, response.request.domain, template)
        else:
          TEMPLATE_CACHE[response.request.key] = None
          response.request.result.reportServiceResult(self, None)
      except Exception, e:
        logging.error("Parse error: %s" % e)
        TEMPLATE_CACHE[response.request.key] = None
        response.request.result.reportServiceResult(self, None)
    else:
      TEMPLATE_CACHE[response.request.key] = None
      response.request.result.reportServiceResult(self, None)    


  def onTemplate(self, result, handler, userid, domain, template):
    userXRDURL = template.replace("{uri}", "%s@%s" % (userid, domain))

    http = tornado.httpclient.AsyncHTTPClient()
    xrdRequest = tornado.httpclient.HTTPRequest(userXRDURL)
    xrdRequest.result = result
    xrdRequest.handler = handler
    http.fetch(xrdRequest, callback=handler.async_callback(self.onXRDResponse))
    
  def onXRDResponse(self, response):
    if response.code == 200:
      try:
        logging.error("Got XRD " + response.body)
        dom = xml.dom.minidom.parseString(response.body)
        links = dom.getElementsByTagName("Link");
        
        returnVal = {}
        for link in links:
          if not "urls" in returnVal: returnVal["urls"] = []          
          rel = link.getAttribute("rel")
          if rel and len(rel):
            type = "data"
            if rel in REL_DICTIONARY:
              type = REL_DICTIONARY[rel]              
            obj = {"type":type, "rel":rel, "value":link.getAttribute("href")}
            if link.hasAttribute("type"):
              obj["content-type"] = link.getAttribute("type")
            returnVal["urls"].append(obj)

        response.request.result.reportServiceResult(self, returnVal)            
      except Exception, e:
        logging.error("XRD error: %s" % e)
        response.request.result.reportServiceResult(self, None)
    else:
      response.request.result.reportServiceResult(self, None)

services.Factory.registerService(WebfingerService())



# Note that the Google Open-Social URL gives:
# {"entry":{"profileUrl":"http://www.google.com/profiles/mhanson","id":"104413556092152528701",
# "name":{"formatted":"Michael Hanson","familyName":"Hanson","givenName":"Michael"},
# "thumbnailUrl":"http://www.google.com/ig/c/photos/public/AIbEiAIAAABDCL3",
# "urls":[{"value":"http://www.google.com/profiles/mhanson","type":"profile"}],
# "photos":[{"value":"http://www.google.com/ig/c/photos/public/AIbEiAIAAABDCL3-","type":"thumbnail"}],
# "displayName":"Michael Hanson"}}


