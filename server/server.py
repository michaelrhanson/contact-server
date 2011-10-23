#!/usr/bin/env python
#
# Contacts server front end
#
# The server module is responsible for incoming and outgoing HTTP requests.
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
import json
from urlparse import urlparse

import google
import gravatar


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




class FacebookConnectHandler(tornado.web.RequestHandler, tornado.auth.FacebookGraphMixin):
  @tornado.web.asynchronous
  def get(self):
    if self.get_argument("code", False):
      self.get_authenticated_user(
        redirect_uri='http://mozillalabs.com/contacts/auth/facebookgraph',
        client_id=self.settings["facebook_api_key"],
        client_secret=self.settings["facebook_secret"],
        code=self.get_argument("code"),
        callback=self.async_callback(
          self._on_login))
      return

    self.authorize_redirect(
      redirect_uri='http://mozillalabs.com/contacts/auth/facebookgraph',
      client_id=self.settings["facebook_api_key"],
      extra_params={"scope": "read_stream,offline_access,friends_about_me,friends_location,friends_checkins,friends_birthday,friends_events,friends_online_presence,friends_photos,friends_status,friends_videos,friends_website,read_friendlists"})

  def _on_login(self, user):
    logging.error(user)
    self.set_cookie("facebook_token", user["access_token"])
    self.redirect("/static/contacts.htm")
    self.finish()

class FacebookRequestHandler(tornado.web.RequestHandler, tornado.auth.FacebookGraphMixin):
  @tornado.web.asynchronous
  def get(self, what):
    token = self.get_cookie("facebook_token")
    self.facebook_request("/" + what, self.async_callback(self._on_finish), token)

  def _on_finish(self, data):
    logging.error(data)
    if data:
      self.write(data)
    self.finish()


##################################################################
# Main Application Setup
##################################################################

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "../site"),
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
#    (r"/listview", ListViewHandler),
#    (r"/user", UserHandler),
#    (r"/user/ids", UserIdentitiesHandler),
#    (r"/user/addid", AddIdentityHandler),

    #(r"/user/services", UserServicesHandler),

    (r"/google/contacts", google.GoogleFetchHandler),
    (r"/google/rsrc", google.GoogleGetResourceHandler),
    (r"/connect/google", google.GoogleConnectHandler),
    (r"/authorize/google", google.GoogleAuthorizeHandler),

#    (r"/fetch/yahoo", yahoo.YahooFetchHandler),
#    (r"/connect/yahoo", yahoo.YahooConnectHandler),
#    (r"/authorize/yahoo", yahoo.YahooAuthorizeHandler),

    (r"/connect/facebook", FacebookConnectHandler),
    (r"/contacts/auth/facebookgraph", FacebookConnectHandler),
    (r"/fb/(.*)", FacebookRequestHandler),
#    (r"/connect/yahoo", YahooConnectHandler),
#    (r"/connect/twitter", TwitterConnectHandler),
#    (r"/connect/flickr", FlickrConnectHandler),

    (r"/gravatar/(.*)", gravatar.GravatarLookupHandler),
    
    (r"/me", MeHandler),
    (r"/", MainHandler),
#    (r"/lookup/(.*)", LookupHandler),
 
	], **settings)

def run():
    http_server = tornado.httpserver.HTTPServer(application)
    #http_server.listen(8300)
    port = 80
    http_server.listen(port)
    print "Starting server on %d" % port
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
	
	