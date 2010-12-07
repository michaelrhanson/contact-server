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
class YahooConnectHandler(tornado.web.RequestHandler, tornado.auth.OpenIdMixin):
  _OPENID_ENDPOINT = "https://open.login.yahooapis.com/openid/op/auth"

  @tornado.web.asynchronous
  def get(self):
    if self.get_argument("openid.mode", None):
      self.get_authenticated_user(self.async_callback(self.onConnect))
      return
    to = self.get_argument("to", None)
    if not to: to = "/"
    self.authenticate_redirect(callback_uri = "http://localhost:8300/connect/yahoo?" + urllib.urlencode({"to":to}))
    
  # Got the response and unpacked OpenID parameters: handle it
  def onConnect(self, claimed_user_data):
    logging.info(claimed_user_data)
  
    if not claimed_user_data:
      logging.warning("Could not log in Yahoo user")
      self.write("unable to connect")
      self.finish()
      return
    
    # Now do we have a user for this Yahoo identity?
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
        logging.info("Yahoo ID %s logged in succesfully to user account %s" % (claimed_id, user.id))
      else:
        # new user
        user = model.User()
        session.add(user)
        id = model.Identity(claimed_id, user, claimed_user_data["name"], model.OP_YAHOO)
        id.verifiedNow()
        session.add(id)
        session.commit()

      self.set_secure_cookie("uid", str(user.id))
      
      # Where to?
    except Exception, e:
      logging.exception(e)
      session.rollback()
    
    to = self.get_argument("to", None)
    if to:
      self.redirect(to)
    else:
      self.redirect("/")

# This works even on localhost - but it doesn't give us the user's ID.
# For now that's okay.  Once we're routable we should be able to do it
# all from YahooConnect and get the access_token in the user object
# passed to onConnect. (i.e. we can chuck this handler)
class YahooAuthorizeHandler(tornado.web.RequestHandler, tornado.auth.OAuthMixin):
  _OAUTH_NO_CALLBACKS = False
  _OAUTH_VERSION = "1.0"
  _OAUTH_REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth/v2/get_request_token"
  _OAUTH_AUTHORIZE_URL     = "https://api.login.yahoo.com/oauth/v2/request_auth"
  _OAUTH_ACCESS_TOKEN_URL  = "https://api.login.yahoo.com/oauth/v2/get_token"


  @tornado.web.asynchronous
  def get(self):
    uid = self.get_secure_cookie("uid")
    if not uid:
      logging.warn("No user session: redirecting to root")
      return self.redirect("/")
      
    if self.get_argument("oauth_token", None):
      self.get_authenticated_user(self.async_callback(self.onConnect))
      return

    to = self.get_argument("to", None)
    if not to: to = "/listview"

    self.authorize_redirect(callback_uri = "http://localhost:8300/authorize/yahoo?" + urllib.urlencode({"to":to}), extra_params = {
      'xoauth_displayname': "Mozilla Contacts"
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
    
    logging.info("Got OAuth callback: %s" % response)
    # NOTE that we assume the user has only one Yahoo account here! 
    access_token = tornado.auth._oauth_parse_response(response.body)
    logging.info(" parsed to: %s" % access_token)

    # What we get back is:
    #  {'xoauth_yahoo_guid': '54MJG4TXXXXXXMDIXXXXX5G5M', 
    #   'oauth_authorization_expires_in': '855808199', 'oauth_expires_in': '3600', 
    #   'oauth_session_handle': 'AHNm_UxwMcc-', 
    #   'secret': '2864f3d82f082cbbcf70b', 
    #   'key': 'A=EDiRDHTtsx3u5W.I9Vj<lots bigger>...'}

    session = model.Session()
    user = model.user(session, uid)
    id = user.identity(session, model.OP_YAHOO)
    if id:
      id.accessToken = access_token["key"]
      id.accessSecret = access_token["secret"]
      id.opaqueID = access_token["xoauth_yahoo_guid"]
      session.add(id)
      session.commit()
    else: # strange, we have no id for this user
      self.write("Whoops - we don't have an authenticated Yahoo login for you.  That's weird.")
      self.finish()
      return
    
    to = self.get_argument("to", None)
    if to:
      self.redirect(to)
    else:
      self.redirect("/")

  def onConnect(self, user):
    logging.error("Made it to onConnect")
    if not user:
      raise tornado.web.HTTPError(500, "Yahoo authorization failed")
    # The access token is in access_token - save it
    logging.error(user)

  def _oauth_consumer_token(self):
      self.require_setting("yahoo_consumer_key", "Yahoo OAuth")
      self.require_setting("yahoo_consumer_secret", "Yahoo OAuth")
      return dict(
          key=self.settings["yahoo_consumer_key"],
          secret=self.settings["yahoo_consumer_secret"])



class YahooFetchHandler(tornado.web.RequestHandler, tornado.auth.OAuthMixin):
  _OAUTH_VERSION = "1.0"

  @tornado.web.asynchronous
  def get(self):
    uid = self.get_secure_cookie("uid")
    if not uid:
      logging.warn("No user session: redirecting to root")
      return self.redirect("/")

    args = {"count":"max", "format":"json"}
    page = self.get_argument("page", None)

    session = model.Session()
    user = model.user(session, uid)
    id = user.identity(session, model.OP_YAHOO)

    access_token = {"key":id.accessToken, "secret":id.accessSecret}
    url = "http://social.yahooapis.com/v1/user/" + id.opaqueID + "/contacts"
      
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
      self.require_setting("yahoo_consumer_key", "Yahoo OAuth")
      self.require_setting("yahoo_consumer_secret", "yahoo OAuth")
      return dict(
          key=self.settings["yahoo_consumer_key"],
          secret=self.settings["yahoo_consumer_secret"])

  def onFetch(self, response):
    if response.code == 401: # need to reauthorize
      self.redirect("/authorize/yahoo?to=/fetch/yahoo")
    else:
      # Convert from GData XML to JSON:
      logging.error(response.body)
      doc = json.loads(response.body)
      logging.error(doc)
      result = {"status":"ok"}
      result["contacts"] = contacts = []

      anonCount = 1
      for aContact in doc["contacts"]["contact"]:
        try:
          person = {}
          contacts.append(person)
          for aField in aContact["fields"]:
            if aField["type"] == "name":
              name = person["name"] = {};
              if aField["value"]["givenName"]: name["givenName"] = aField["value"]["givenName"]
              if aField["value"]["familyName"]: name["familyName"] = aField["value"]["familyName"]
              if aField["value"]["middleName"]: name["middleName"] = aField["value"]["middleName"]
              if aField["value"]["prefix"]: name["prefix"] = aField["value"]["prefix"]
              if aField["value"]["suffix"]: name["suffix"] = aField["value"]["suffix"]

            elif aField["type"] == "phone":
              if not "phoneNumbers" in person: person["phoneNumbers"] = [];
              aPhone = {}
              aPhone["value"] = aField["value"];
              if aField["flags"] and len(aField["flags"]) > 0:
                aPhone["type"] = aField["flags"][0].lower()
              else:
                aPhone["type"] = "unlabeled"

              person["phoneNumbers"].append(aPhone)

            elif aField["type"] == "address":
              if not "addresses" in person: person["addresses"] = []
              anAddress = {}
              if aField["value"]["street"]: anAddress["streetAddress"] = aField["value"]["street"]
              if aField["value"]["city"]: anAddress["locality"] = aField["value"]["city"]
              if aField["value"]["stateOrProvince"]: anAddress["region"] = aField["value"]["stateOrProvince"]
              if aField["value"]["postalCode"]: anAddress["postalCode"] = aField["value"]["postalCode"]
              if aField["value"]["country"]: anAddress["country"] = aField["value"]["country"]
              if aField["value"]["countryCode"]: anAddress["countryCode"] = aField["value"]["countryCode"]
              if aField["flags"] and len(aField["flags"]) > 0:
                anAddress["type"] = aField["flags"][0].lower()
              else:
                anAddress["type"] = "unlabeled"

              person["addresses"].append(anAddress)

            elif aField["type"] == "email":
              if not "emails" in person: person["emails"] = []
              anEmail = {}
              anEmail["value"] = aField["value"]
              if aField["flags"] and len(aField["flags"]) > 0:
                anEmail["type"] = aField["flags"][0].lower()
              else:
                anEmail["type"] = "internet"

              person["emails"].append(anEmail)

            elif aField["type"] == "yahooid":
              if not "accounts" in person: person["accounts"] = []
              person["accounts"].append({"type":"yahoo", "username":aField["value"], "domain":"yahoo.com"})
            
            elif aField["type"] == "otherid":

              if aField["flags"] and len(aField["flags"]) > 0:
                flag = aField["flags"][0]
                domain = None
                type = None
                
                if flag == "GOOGLE":
                  domain = "google.com"
                  type = "google"
                elif flag == "ICQ":
                  domain = "icq.com"
                  type = "ICQ"
                elif flag == "JABBER":
                  domain = "jabber"
                  type = "Jabber"
                elif flag == "MSN":
                  domain = "msn.com"
                  type = "MSN"
                elif flag == "SKYPE":
                  domain = "skype.com"
                  type = "skype"
                else:
                  domain = flag.lower()
                  type = flag.lower()

                if not "accounts" in person: person["accounts"] = []
                person["accounts"].append({"type":type, "username":aField["value"], "domain":domain});

            elif aField["type"] == "link":

              if aField["flags"] and len(aField["flags"]) > 0:
                flag = aField["flags"][0]
                type = flag.lower();

                if not "urls" in person: person.urls = []
                person["urls"].push({"type":type, "value":aField["value"]})
            elif aField["type"] == "company":

              if not person["organizations"]: person["organizations"] = [{}]
              person["organizations"][0].name = aField["value"];

            elif aField["type"] == "jobTitle":
              if not person["organizations"]:person["organizations"] = [{}]
              person["organizations"][0]["title"] = aField["value"];

            # Construct a display name:
            if "name" in person:
              if "givenName" in person["name"] and "familyName" in person["name"]:
                person["displayName"] = person["name"]["givenName"] + " " + person["name"]["familyName"] # FIXME Eurocentric
              elif "givenName" in person["name"]:
                person["displayName"] = person["name"]["givenName"]
              elif "familyName" in person["name"]:
                person["displayName" ]= person["name"]["familyName"]

#            if not person["displayName"] and person["accounts"]:
#              for p in person["accounts"]:
#                if p["domain"] == "yahoo.com":
#                  person["displayName"] = p["username"]
#                  break

#            if not person["displayName"]: person["displayName"] = person["accounts"][0]["username"]
#            if not person["displayName"] and person["emails"]:
#              person["displayName"] = person.emails[0]["value"];
#          }
#          if (!person.displayName) {
#            person.displayName = "Unnamed Yahoo Contact " + anonCount;
#            anonCount += 1;
#          }


        except Exception, e:
          logging.exception(e)
          pass
      self.write(json.dumps(result))
      self.finish()

#        
#          // Construct a display name:
#          if (person.name) {
#            if (person.name.givenName && person.name.familyName) {
#              person.displayName = person.name.givenName + " " + person.name.familyName; // FIXME Eurocentric
#            } else if (person.name.givenName) {
#              person.displayName = person.name.givenName;
#            } else if (person.name.familyName) {
#              person.displayName = person.name.familyName;            
#            }
#          } else {
#            person.name = {givenName:"", familyName:""};
#          }
#          
#          if (!person.displayName && person.accounts) {
#            for each (p in person.accounts) {
#              if (p.domain == "yahoo.com") {
#                person.displayName = p.username;
#                break;
#              }
#            }
#            if (!person.displayName) person.displayName = person.accounts[0].username;
#          }
#          if (!person.displayName && person.emails) {
#            person.displayName = person.emails[0]["value"];
#          }
#          if (!person.displayName) {
#            person.displayName = "Unnamed Yahoo Contact " + anonCount;
#            anonCount += 1;
#          }
#          people.push(person);
#        } catch (e) {
#          this._log.info("Error importing Yahoo contact: " + e);
#        }
#      }#


#      self.write(json.dumps(result))
#      self.finish()
      
