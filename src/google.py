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

import gravatar
import model  # replace this with a dbserver
import xmlreader
   

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
    self.authenticate_redirect(callback_uri = "http://localhost:8300/connect/google?" + urllib.urlencode({"to":to}))
    
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

    try:
      session = model.Session()
      id_list = model.identity(session, claimed_id)
      if id_list and len(id_list) > 0:
        if len(id_list) > 1: # uh oh
          self.write("More than one user has claimed this identity.  That's confusing.  We should try to merge them somehow?")
          self.finish()
          return
          
        user = id_list[0].user
        logging.info("Google ID %s logged in succesfully to user account %s" % (claimed_id, user.id))
      else:
        # new user
        user = model.User()
        session.add(user)
        id = model.Identity(claimed_id, user, claimed_user_data["name"], model.OP_GOOGLE)
        id.verifiedNow()
        session.add(id)
        session.commit()

      self.set_secure_cookie("uid", str(user.id))
      
      # Where to?
    except Exception, e:
      logging.exception(e)
      session.rollback()
    
    #self.write("Success.  <a href='/fetch/google?" + urllib.urlencode(user["access_token"]) + "'>Load Google Contacts</a>")
    to = self.get_argument("to", None)
    if to:
      self.redirect(to)
    else:
      self.redirect("/")

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
    uid = self.get_secure_cookie("uid")
    if not uid:
      logging.warn("No user session: redirecting to root")
      return self.redirect("/")
      
    if self.get_argument("oauth_token", None):
      self.get_authenticated_user(self.async_callback(self.onConnect))
      return
    self.authorize_redirect(callback_uri = "http://localhost:8300/authorize/google", extra_params = {
      'xoauth_displayname': "Mozilla Contacts",
      'scope': 'http://www.google.com/m8/feeds' # /contacts'
    })
    
  def _on_access_token(self, callback, response):
    if response.error:
        logging.warning("Could not fetch access token")
        callback(None)
        return

    uid = self.get_secure_cookie("uid")
    if not uid:
      logging.warn("No user session: redirecting to root")
      return self.redirect("/")
    
    # NOTE that we assume the user has only one GMail account here! 
    # This may be okay given that Google is moving towards single-login/multiple-account
    # but it could be a problem.
    access_token = tornado.auth._oauth_parse_response(response.body)
    session = model.Session()
    user = model.user(session, uid)
    id = user.identity(session, model.OP_GOOGLE)
    if id:
      id.accessToken = access_token["key"]
      id.accessSecret = access_token["secret"]
      session.add(id)
      session.commit()
    else: # strange, we have no id for this user
      self.write("Whoops - we don't have an authenticated Google login for you.  That's weird.")
      self.finish()
      return
    
    self.write("Success.  Saved access codes for Google.  <a href='/fetch/google'>Take a look</a>")
    self.finish()

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
    uid = self.get_secure_cookie("uid")
    if not uid:
      logging.warn("No user session: redirecting to root")
      return self.redirect("/")

    args = {"max-results":1000}
    page = self.get_argument("page", None)

    session = model.Session()
    user = model.user(session, uid)
    id = user.identity(session, model.OP_GOOGLE)

    access_token = {"key":id.accessToken, "secret":id.accessSecret}
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
      logging.error(doc)
      result = {"status":"ok"}
      result["contacts"] = contacts = []
      if "entry" in doc:
        for entry in doc["entry"]:
          person = {}
          contacts.append(person)
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
                  photos.append({ "value": "http://localhost:8300/getresource/google?" + urllib.urlencode({"rsrc":link["@href"]}), "type": link["@type"] })

      self.write(json.dumps(result))
      self.finish()
      
class GoogleGetResourceHandler(tornado.web.RequestHandler, tornado.auth.OAuthMixin):
  @tornado.web.asynchronous
  def get(self):

    uid = self.get_secure_cookie("uid")
    if not uid:
      logging.warn("No user session: redirecting to root")
      return self.redirect("/")

    session = model.Session()
    user = model.user(session, uid)
    id = user.identity(session, model.OP_GOOGLE)
    access_token = {"key":id.accessToken, "secret":id.accessSecret}

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
      
