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
import json
from urlparse import urlparse

#import gravatar
#import model  # replace this with a dbserver
import xmlreader
import webconfig
   

# The OpenID+OAuth hybrid stuff doesn't work for us because (AFAICT) we're not
# world-routable yet.  So this is just doing authentication and then we hand
# off to the authorizer.
class GoogleConnectHandler(tornado.web.RequestHandler, tornado.auth.GoogleMixin):
  @tornado.web.asynchronous
  def get(self):
    if self.get_argument("openid.mode", None):
      self.get_authenticated_user(self.async_callback(self.onConnect))
      return
    to = self.get_argument("to", None)
    if not to: to = "/"
    self.authenticate_redirect(callback_uri = "http://%s/connect/google?%s" % (
      webconfig.HOSTNAME, urllib.urlencode({"to":to})))
    
  # Got the response and unpacked OpenID parameters: handle it
  def onConnect(self, claimed_user_data):
    if not claimed_user_data:
      logging.warning("Could not log in Google user")
      self.write("unable to connect")
      self.finish()
      return
    
    # Now do we have a user for this Google identity?
    claimed_id = claimed_user_data["claimed_id"] if "claimed_id" in claimed_user_data else claimed_user_data["email"]
    if not claimed_id:
      self.write("unable to get an identifier")
      self.finish()
      return 

    self.set_secure_cookie("google_id", claimed_id)

    self.write("Got identity %s" % claimed_id)
    self.finish()
    #self.set_secure_cookie("google_token", claimed_user_data["access_token"])
    #self.write("Success.  <a href='/fetch/google?" + urllib.urlencode(claimed_user_data["access_token"]) + "'>Load Google Contacts</a>")
    #to = self.get_argument("to", None)
    #if to:
    #  self.redirect(to)
    #else:
    #  self.redirect("/")

# This works even on localhost - but it doesn't give us the user's ID.
# For now that's okay.  Once we're routable we should be able to do it
# all from GoogleConnect and get the access_token in the user object
# passed to onConnect. (i.e. we can chuck this handler)
class GoogleAuthorizeHandler(tornado.web.RequestHandler, tornado.auth.OAuthMixin):
  _OAUTH_REQUEST_TOKEN_URL = "https://www.google.com/accounts/OAuthGetRequestToken"
  _OAUTH_ACCESS_TOKEN_URL = "https://www.google.com/accounts/OAuthGetAccessToken"
  _OAUTH_AUTHORIZE_URL = "https://www.google.com/accounts/OAuthAuthorizeToken"
  _OAUTH_NO_CALLBACKS = False

  @tornado.web.asynchronous
  def get(self):
    #uid = self.get_secure_cookie("google_id")
    #if not uid:
    #  logging.warn("No user session: redirecting to root")
    #  return self.redirect("/")
      
    if self.get_argument("oauth_token", None):
      self.get_authenticated_user(self.async_callback(self.onConnect))
      return
    self.authorize_redirect(callback_uri = "http://%s/authorize/google" % webconfig.HOSTNAME, extra_params = {
      'xoauth_displayname': "Mozilla Contacts",
      'scope': 'http://www.google.com/m8/feeds' # /contacts'
    })
    
  def _on_access_token(self, callback, response):
    if response.error:
        logging.warning("Could not fetch access token")
        callback(None)
        return

    #uid = self.get_secure_cookie("google_id")
    #if not uid:
    #  logging.warn("No user session: redirecting to root")
    #  return self.redirect("/")
    
    # NOTE that we assume the user has only one GMail account here! 
    # This may be okay given that Google is moving towards single-login/multiple-account
    # but it could be a problem.
    access_token = tornado.auth._oauth_parse_response(response.body)
    self.set_secure_cookie("google_key", access_token["key"])
    self.set_secure_cookie("google_secret", access_token["secret"])
    self.redirect("/static/contacts.htm")
    #self.write("Success.  Saved access codes for Google.  <a href='/fetch/google'>Take a look</a>")
    #self.finish()

  def onConnect(self, user):
    logging.error("Made it to onConnect")
    if not user:
      raise tornado.web.HTTPError(500, "Google authorization failed")
    # The access token is in access_token - save it
    logging.error(user)

  def _oauth_consumer_token(self):
      self.require_setting("google_consumer_key", "Google OAuth")
      self.require_setting("google_consumer_secret", "Google OAuth")
      return dict(
          key=self.settings["google_consumer_key"],
          secret=self.settings["google_consumer_secret"])



class GoogleFetchHandler(tornado.web.RequestHandler, tornado.auth.OAuthMixin):
  @tornado.web.asynchronous
  def get(self):
    #uid = self.get_secure_cookie("google_id")
    #if not uid:
    #  logging.warn("No user session: redirecting to root")
    #  return self.redirect("/")

    args = {"max-results":1000}
    page = self.get_argument("page", None)

    key = self.get_secure_cookie("google_key")
    secret = self.get_secure_cookie("google_secret")

    access_token = {"key":key, "secret":secret}
    url = "http://www.google.com/m8/feeds/contacts/default/full"
      
    if access_token:
        all_args = {}
        all_args.update(args)
        consumer_token = self._oauth_consumer_token()
        oauth = self._oauth_request_parameters(url, access_token, all_args, method="GET")
        args.update(oauth)

    if args: url += "?" + urllib.urlencode(args)
    callback = self.async_callback(self.onFetch)
    http = tornado.httpclient.AsyncHTTPClient()
    http.fetch(url, callback=callback)

  def _oauth_consumer_token(self):
      self.require_setting("google_consumer_key", "Google OAuth")
      self.require_setting("google_consumer_secret", "Google OAuth")
      return dict(
          key=self.settings["google_consumer_key"],
          secret=self.settings["google_consumer_secret"])

  def onFetch(self, response):
    if response.code == 401: # need to reauthorize
      self.write("Whoops, authorization failure.  Probably need to reauthorize.")
      self.finish()
    else:
      # Convert from GData XML to JSON:
      doc = xmlreader.read(response.body)
      #logging.error(doc)
      result = {"status":"ok"}
      result["contacts"] = contacts = []
      if "entry" in doc:
        for entry in doc["entry"]:
          #logging.error(entry)
          person = {}
          contacts.append(person)
          if "id" in entry:
            person["id"] = entry["id"][0]
          if "title" in entry:
            t = entry["title"]
            if len(t) > 0:
              t = entry["title"][0]
              if "text()" in t:
                person["displayName"] = t["text()"]
          if "gd:email" in entry:
            emails = person["emails"] = []
            for email in entry["gd:email"]:
              emails.append( { "value" : email["@address"] } )
          if "link" in entry:
            photos = None
            for link in entry["link"]:
              if "@rel" in link:
                if link["@rel"] == "http://schemas.google.com/contacts/2008/rel#photo":
                  if not photos: 
                    person["photos"] = photos = []
                  href = link["@href"]
                  photos.append({ 
                    "value": "http://%s/google/rsrc?%s" % (
                        webconfig.HOSTNAME, urllib.urlencode({"rsrc":link["@href"]})), 
                    "type": link["@type"] 
                  })

      self.write(json.dumps(result))
      self.finish()
      
class GoogleGetResourceHandler(tornado.web.RequestHandler, tornado.auth.OAuthMixin):
  @tornado.web.asynchronous
  def get(self):

    #uid = self.get_secure_cookie("google_id")
    #if not uid:
    #  logging.warn("No user session: redirecting to root")
    #  return self.redirect("/")

    key = self.get_secure_cookie("google_key")
    secret = self.get_secure_cookie("google_secret")
    access_token = {"key":key, "secret":secret}

    # TODO could fill in arguments here...
    args = {}
    post_args = None

    rsrc = self.get_argument("rsrc", None)
    url = rsrc
      
    if access_token:
        all_args = {}
        all_args.update(args)
        consumer_token = self._oauth_consumer_token()
        method = "POST" if post_args is not None else "GET"
        oauth = self._oauth_request_parameters(
            url, access_token, all_args, method=method)
        args.update(oauth)
    if args: url += "?" + urllib.urlencode(args)
    callback = self.async_callback(self.onFetch)
    http = tornado.httpclient.AsyncHTTPClient()
    if post_args is not None:
        http.fetch(url, method="POST", body=urllib.urlencode(post_args),
                   callback=callback)
    else:
        http.fetch(url, callback=callback)

  def _oauth_consumer_token(self):
      self.require_setting("google_consumer_key", "Google OAuth")
      self.require_setting("google_consumer_secret", "Google OAuth")
      return dict(
          key=self.settings["google_consumer_key"],
          secret=self.settings["google_consumer_secret"])

  def onFetch(self, response):
    self.set_header("Content-Type", response.headers["Content-Type"])
    self.write(response.body)
    self.finish()
      
