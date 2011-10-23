import tornado.httpclient
import hashlib
import json

class GravatarLookupHandler(tornado.web.RequestHandler):

  @tornado.web.asynchronous
  def get(self, address):
    md5 = hashlib.md5(address).hexdigest()
      
    # check for avatar
    http = tornado.httpclient.AsyncHTTPClient()
    avatarRequest = tornado.httpclient.HTTPRequest("http://www.gravatar.com/avatar/" + md5 + "?d=404&s=1")
    avatarRequest.md5 = md5
    http.fetch(avatarRequest, callback=self.async_callback(self.onAvatarResponse))

  def onAvatarResponse(self, response):
    if response.code == 200:
      # Okay, they have an avatar - go ahead and see if they have a profile too
      http = tornado.httpclient.AsyncHTTPClient()
      profileRequest = tornado.httpclient.HTTPRequest("http://www.gravatar.com/" + response.request.md5 + ".json")
      profileRequest.md5 = response.request.md5
      http.fetch(profileRequest, callback=self.async_callback(self.onProfileResponse))
    else:
      self.write("{}")
      self.finish()
      
  def onProfileResponse(self, response):
    if response.code == 200:
      # Great, got some JSON
      res = json.loads(response.body)
      
      # normalize back to the way we expect 
      # PoCo to be used... :(
      if "entry" in res:
        p = res["entry"][0]
        if "name" in p and "formatted" in p["name"]:
          p["displayName"] = p["name"]["formatted"]
        if "aboutMe" in p:
          p["note"] = p["aboutMe"]
        if "thumbnailUrl" in p:
          del p["thumbnailUrl"]
        if "hash" in p:
          del p["hash"]

        self.write(json.dumps(p))
      else:
        self.write("{}")
      self.finish()
    else:
      # Just an avatar then
      self.write(
        {"photos":
          [{"type":"thumbnail",
            "value":"http://www.gravatar.com/avatar/" + response.request.md5}]})
      self.finish()

