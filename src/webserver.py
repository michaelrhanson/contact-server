#!/usr/bin/env python
#
# Contacts server front end
#
# The webserver module is responsible for incoming and outgoing HTTP requests.
#

import tornado.httpserver
import tornado.auth
import tornado.ioloop
import tornado.web
import os
import re
import time
import calendar
import base64
import traceback
import logging
import urllib
import cStringIO
import json
import cgi
import webconfig
import json
from urlparse import urlparse

import services
import gravatar
import flickr
import webfinger
import hcard
import model  # replace this with a dbserver
import xmlreader
import google
import yahoo

class WebHandler(tornado.web.RequestHandler):
  def getCurrentUser(self):
    return None
   
class MainHandler(WebHandler):
	def get(self):
		self.render("index_no_user.html", errorMessage=None)

class ListViewHandler(WebHandler):
	def get(self):
		self.render("listview.html", errorMessage=None)

class MeHandler(WebHandler):
	def get(self):
		pass

class LookupHandler(WebHandler):
  @tornado.web.asynchronous
  def get(self, identifier):
    # Simple approach for now:
    # Just hit all of our available resources and don't return until
    # we've got data from all of them.
    
    # Resolve the current user session, if any
    user = self.getCurrentUser()
    result = services.Result(self.async_callback(self.onServiceResult))

    serviceList = services.Factory.getServicesForIdentifier(identifier)
    self.request.serviceResult = result

    # Start all service lookups
    if len(serviceList):
      for svc in serviceList:
        result.addPendingService(svc)

      for svc in serviceList:
        svc.lookup(self, identifier, result, user)
    else:
      self.write("{}\n")
      self.finish()
    
  
  # If we have data from all services, return
  def onServiceResult(self):
    if not self.request.serviceResult.anyPendingServices():
      self.write(self.request.serviceResult.renderJSON())
      self.finish()

class UserHandler(WebHandler):
  def get(self):
    uid = self.get_secure_cookie("uid")
    if uid:
      self.write('{"uid":%s}' % uid)
    else:
      self.write('{}')
    
class UserIdentitiesHandler(WebHandler):
  @tornado.web.asynchronous
  def get(self):
    uid = self.get_secure_cookie("uid")
    if uid:
      http = tornado.httpclient.AsyncHTTPClient()
      request = tornado.httpclient.HTTPRequest("%s/user?uid=%s" % (webconfig.DB_URL, uid))
      http.fetch(request, callback=self.async_callback(self.onResponse))
    else:
      raise tornado.web.HTTPError(403)

  def onResponse(self, response):
    if response.code == 200:
      self.write(response.body)
      self.finish()
    else:
      raise tornado.web.HTTPError(500)


class UserServicesHandler(WebHandler):
  def get(self):
    uid = self.get_secure_cookie("uid")
    if not uid:
      return self.write("""{status:"error", message:"No user session"}""")

    session = model.Session()
    user = model.user(session, uid)
    result = {"status":"ok"}
    services = result["services"] = []
    for anID in user.identities:
      services.append(anID.name())

    self.set_header("Content-Type", "text/json")
    self.write(json.dumps(result))

class AddConnectHandler(WebHandler):
  @tornado.web.asynchronous
  def get(self):
    idService = self.request.arguments["svc"][0]
    

class FacebookIdentityHandler(tornado.web.RequestHandler, tornado.auth.FacebookMixin):
  @tornado.web.asynchronous
  def get(self):
    if self.get_argument("session", None):
        self.get_authenticated_user(self.async_callback(self._on_auth))
        return
    self.authenticate_redirect()

  def _on_auth(self, user):
    if not user:
        raise tornado.web.HTTPError(500, "Facebook auth failed")

    uid = self.get_secure_cookie("uid")
    if not uid:
      http = tornado.httpclient.AsyncHTTPClient()
      request = tornado.httpclient.HTTPRequest("%s/user" % (webconfig.DB_URL,), method="POST", body="")
      request.authResult = user
      http.fetch(request, callback=self.async_callback(self.onUserCreation))
    else:
      self.onAuthentication(uid, user)
    
  def onUserCreation(self, response):
    if response.code == 200:
      res = json.loads(response.body)
      if res["status"] == "ok":
        uid = res["uid"]
        self.set_secure_cookie("uid", str(uid))
        self.onAuthentication(uid, response.request.authResult)
      else:
        raise tornado.web.HTTPError(500)        
    else:
      raise tornado.web.HTTPError(500)
          
  def onAuthentication(self, uid, userData):
    logging.error(userData)
    # Will be like {'locale': u'en', 'first_name': u'Michael', 'last_name': u'Hanson', 'name': u'Michael Hanson', 'email': u'mhanson@gmail.com'}    
    # http://mozillalabs.com/contacts/?session=
    # {%22session_key%22%3A%222.yckrLpRNm1IifvZMkD9tcA__.3600.1285653600-562624793%22%2C%22uid%22%3A562
    # 624793%2C%22expires%22%3A1285653600%2C%22secret%22%3A%220iTnAkNTENnb8R6J1q1YJw__%22%2C%22sig%22%3A%223
    # 298b3435f8c78b63e165a09db160a68%22}&next=http%3A%2F%2Flocalhost%3A8300%2Fuser%2Faddid%2Ffacebook
    
    http = tornado.httpclient.AsyncHTTPClient()
    body = {"uid":uid, "identifier":userData["email"], "displayName":userData["name"], "opaqueID": userData["facebook_uid"], "sessionKey": userData["session_key"] }

    request = tornado.httpclient.HTTPRequest("%s/id" % (webconfig.DB_URL,), method="POST", body=urllib.urlencode(body))
    request.uid = uid
    http.fetch(request, callback=self.async_callback(self.onIdentitySaved))

  def onIdentitySaved(self, response):
    if response.code == 200:
      self.write('{"status":"ok", "uid": %s}' % response.request.uid)
      self.finish()
    else:
      raise tornado.web.HTTPError(500)



##################################################################
# Main Application Setup
##################################################################

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "B44CCD51-E21D-4D39-AFB7-03E4ED220733",
    "login_url": "/login",
    "debug":True,
    
    "facebook_api_key":"873bb1ddcc201222004c053a25d07d12",
    "facebook_secret":"5a931183e640fa50ca93b0ab556eb949",

    "yahoo_consumer_key": "dj0yJmk9Qm9TNnJlY3FaVDNVJmQ9WVdrOU9YRkhNWGxMTjJzbWNHbzlPVFF6TURRNE5EWTEmcz1jb25zdW1lcnNlY3JldCZ4PTNi",
    "yahoo_consumer_secret": "b50f90fcc9b237da8272c8156cf5c4e202c5b5e4",

    "google_consumer_key":"anonymous",
    "google_consumer_secret":"anonymous"
#    "xsrf_cookies": True,
}

application = tornado.web.Application([
    (r"/listview", ListViewHandler),
    (r"/user", UserHandler),
    (r"/user/ids", UserIdentitiesHandler),
#    (r"/user/addid", AddIdentityHandler),

    (r"/user/services", UserServicesHandler),

    (r"/fetch/google", google.GoogleFetchHandler),
    (r"/getresource/google", google.GoogleGetResourceHandler),
    (r"/connect/google", google.GoogleConnectHandler),
    (r"/authorize/google", google.GoogleAuthorizeHandler),

    (r"/fetch/yahoo", yahoo.YahooFetchHandler),
    (r"/connect/yahoo", yahoo.YahooConnectHandler),
    (r"/authorize/yahoo", yahoo.YahooAuthorizeHandler),

#    (r"/connect/facebook", FacebookConnectHandler),
#    (r"/connect/yahoo", YahooConnectHandler),
#    (r"/connect/twitter", TwitterConnectHandler),
#    (r"/connect/flickr", FlickrConnectHandler),
    
    (r"/me", MeHandler),
    (r"/", MainHandler),
    (r"/lookup/(.*)", LookupHandler),
 
	], **settings)

def run():
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8300)
    tornado.ioloop.IOLoop.instance().start()
		
import logging
import sys
if __name__ == '__main__':
	if '-test' in sys.argv:
		import doctest
		doctest.testmod()
	else:
		logging.basicConfig(level = logging.DEBUG)
		run()
	
	