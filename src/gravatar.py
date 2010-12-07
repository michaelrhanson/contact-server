import tornado.httpclient
import services
import hashlib
import json

class GravatarService(object):
  def getName(self):
    return "gravatar"
    
  def lookup(self, handler, identifier, result, user):
    md5 = hashlib.md5(identifier).hexdigest()
      
    # check for avatar
    http = tornado.httpclient.AsyncHTTPClient()
    avatarRequest = tornado.httpclient.HTTPRequest("http://www.gravatar.com/avatar/" + md5 + "?d=404&s=1")
    avatarRequest.result = result
    avatarRequest.md5 = md5
    avatarRequest.handler = handler
    http.fetch(avatarRequest, callback=handler.async_callback(self.onAvatarResponse))

  def onAvatarResponse(self, response):
    if response.code == 200:
      # Okay, they have an avatar - go ahead and see if they have a profile too
      http = tornado.httpclient.AsyncHTTPClient()
      profileRequest = tornado.httpclient.HTTPRequest("http://www.gravatar.com/" + response.request.md5 + ".json")
      profileRequest.result = response.request.result
      profileRequest.md5 = response.request.md5
      http.fetch(profileRequest, callback=response.request.handler.async_callback(self.onProfileResponse))
    else:
      response.request.result.reportServiceResult(self, None)

  def onProfileResponse(self, response):
    if response.code == 200:
      # Great, got some JSON
      res = json.loads(response.body)
      
      # normalize it back to PoCo -- TODO this shouldn't be necessary?
      if "entry" in res:
        response.request.result.reportServiceResult(self, res["entry"][0])
      else:
        response.request.result.reportServiceResult(self, {})      
    else:
      # Just an avatar then
      response.request.result.reportServiceResult(self, 
        {"photo":
          {"type":"thumbnail",
            "value":"http://www.gravatar.com/avatar/" + response.request.md5}})


services.Factory.registerService(GravatarService())