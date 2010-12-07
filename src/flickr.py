import tornado.httpclient
import services
import json
import logging

FLICKR_API_KEY = "c0727ed63fc7eef37d8b46c57eec4b2e"

class FlickrService(object):
  def getName(self):
    return "flickr"
    
  def lookup(self, handler, identifier, result, user):

    if identifier.find("@") < 0 or identifier.find("http:") == 0 or identifier.find("https:") == 0:
      result.reportServiceResult(self, None)
      return

    http = tornado.httpclient.AsyncHTTPClient()
    outRequest = tornado.httpclient.HTTPRequest(
      "http://api.flickr.com/services/rest/?method=flickr.people.findByEmail&api_key=" + FLICKR_API_KEY + 
      "&find_email=" + identifier + "&format=json&nojsoncallback=1")

    outRequest.result = result
    outRequest.handler = handler
    http.fetch(outRequest, callback=handler.async_callback(self.onResponse))

  def onResponse(self, response):
    if response.code == 200:
      res = json.loads(response.body)
      if "stat" in res and res["stat"] == "ok":
        # success looks like:
        # {"stat": "ok", "user": {"username": {"_content": "borkazoid"}, "id": "44124479801@N01", "nsid": "44124479801@N01"}},
        acct = {"domain":"flickr.com"}

        try: acct["username"] = res["user"]["username"]["_content"]
        except: pass
          
        try: acct["userid"] = res["user"]["nsid"]
        except: pass
        
        # not sure what "id" is used for

        # Now get user details
        http = tornado.httpclient.AsyncHTTPClient()
        request = tornado.httpclient.HTTPRequest("http://api.flickr.com/services/rest/?method=flickr.people.getInfo&api_key=" + 
          FLICKR_API_KEY + "&user_id=" + acct["userid"] + "&format=json&nojsoncallback=1")
        request.result = response.request.result
        request.acct = acct
        http.fetch(request, callback=response.request.handler.async_callback(self.onGetInfoResponse))
      else:
        response.request.result.reportServiceResult(self, None)            
    else:
      response.request.result.reportServiceResult(self, None)

  def onGetInfoResponse(self, response):
    if response.code == 200:
      # Success looks like:
      # {"person":
      #     {"id":"44124479801@N01", "nsid":"44124479801@N01", "ispro":1, "iconserver":"1", "iconfarm":1, 
      #      "path_alias":"borkazoid", "username":{"_content":"borkazoid"}, "realname":{"_content":"Beau Lebens"}, 
      #      "location":{"_content":"San Francisco, United States"}, 
      #      "photosurl":{"_content":"http:\/\/www.flickr.com\/photos\/borkazoid\/"}, 
      #      "profileurl":{"_content":"http:\/\/www.flickr.com\/people\/borkazoid\/"}, 
      #      "mobileurl":{"_content":"http:\/\/m.flickr.com\/photostream.gne?id=27888"}, 
      #      "photos":
      #          {"firstdatetaken":{"_content":"2002-08-10 15:56:20"}, 
      #           "firstdate":{"_content":"1095754837"}, 
      #           "count":{"_content":2195}}},
      # "stat":"ok"}

      res = json.loads(response.body)
      if "stat" in res and res["stat"] == "ok":
        returnVal = {"accounts":[response.request.acct]}

        try: realname = res["person"]["realname"]["_content"]
        except: realname = None
        try: location = res["person"]["location"]["_content"]
        except: location = None
        try: photosurl = res["person"]["photosurl"]["_content"]
        except: photosurl = None
        
        # parse real name as best we can:
        if realname:
          returnVal["displayName"] = realname
              
          # For now, let's assume European-style givenName familyName+
          split = realname.split(" ", 1)
          if (len(split) == 2 and len(split[0]) > 0 and len(split[1]) > 0):
            returnVal["name"] = {"givenName":split[0], "familyName":split[1]}

        if location: # feeling confident?  we could parse the location...
          returnVal["location"] = [ {"type":"Location", "value":location} ]
        if photosurl:
          returnVal["urls"] = [ {"type":"Flickr", "value":photosurl, "title":"Flickr Photo Page"} ]

        response.request.result.reportServiceResult(self, returnVal)

      else:
        # Just the account then
        response.request.result.reportServiceResult(self, {"accounts":[ response.request.acct ] })
    
    else:
      response.request.result.reportServiceResult(self, {"accounts":[ response.request.acct ] })


services.Factory.registerService(FlickrService())