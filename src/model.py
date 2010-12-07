# Database model for dbserver

import logging
import re
import os
import subprocess
import simplejson as json
from datetime import datetime

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import ForeignKey, Unicode, DateTime, Column, MetaData, Integer, Text, Boolean, String
from sqlalchemy.orm import relationship, backref
from dbconfig import engine, Session
import sqlalchemy.exc

# SQLAlchemy setup:
metadata = MetaData(engine)
Base = declarative_base(metadata=metadata)

# Validation regexes:
manifest_id_re = re.compile(r'^[a-z0-9_]+$', re.I)

# Object Person
class Person(Base):      
    __tablename__ = "person"
    
    id = Column(Integer, primary_key=True)
    displayName = Column(Text, nullable=False)          # if any
    profile = Column(Text)                              # this is the JSON blob
    primary = Column(Boolean, default=False)            # if True, this Person represents its Owner
    owner_id = Column(Integer, ForeignKey("users.id"))
    updated = Column(DateTime)
    # TODO perhaps a thumbnail URL?
    # email indexing will require another table.
    
    def __init__(self, isPrimary, displayName, profile, ownerid, updated):
      self.displayName = displayName
      self.profile = profile
      self.primary = isPrimary
      self.owner_id = ownerid
      self.updated = updated
    
    def __repr__(self):
      return "<Person(%d, %s, %s, %s)>" % (self.id, self.name, self.primary, self.profile)

# Object User
class User(Base):      
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    identities = relationship("Identity", backref="user")
    
    def __init__(self):
      pass
      
    def __repr__(self):
      return "<User(%s)>" % (self.id)

    def identity(self, session, provider):  
      # Note assumption that there's just one here.  FIX?
      return session.query(Identity).filter(Identity.user_id == self.id).filter(Identity.provider == provider).first()

# Object Identity
class Identity(Base):      
    __tablename__ = "identities"

    id = Column(Integer, primary_key=True)
    provider = Column(Integer)
    identifier = Column(Text)  # the claimedID in OpenID; an <domain:opaque identifier> token for others
    displayName = Column(Text)
    opaqueID = Column(String(128)) # used for whatever GUID or identifier the site needs, e.g. a Yahoo! guid, FB ID, etc.
    accessToken = Column(Text)  # these are sometimes really big!  using Text to be safe.
    accessSecret = Column(Text)
    email = Column(String(128))
    photoURL = Column(String(128))
    verifiedDate = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))

    def __init__(self, identifier, user, displayName, providerID, opaqueID=None):
      self.identifier = identifier
      self.user = user
      self.displayName = displayName
      self.provider = providerID
      if opaqueID: self.opaqueID = opaqueID

    def __repr__(self):
      return "<Identity(%d, %s)>" % (self.id, self.identifier)

    def verifiedNow(self):
      self.verifiedDate = datetime.now()
      
    def name(self):
      return IDENTITY_PROVIDERS[self.provider]
      

# If this is our first run, go take care of housekeeping
metadata.create_all(engine) 

# Someday, replace this with something cleverer.  Not sure what
# that will need to be yet, so, KISS.
OP_GOOGLE = 1
OP_YAHOO = 2
IDENTITY_PROVIDERS =  {
  OP_GOOGLE: "google",
  OP_YAHOO: "yahoo"
}
IDENTITY_PROVIDERS_MAP =  {
  "google":OP_GOOGLE,
  "yahoo":OP_YAHOO
}

    
def person(session, id, userid):
  return session.query(Person).filter(owner_id == userid).filter(id == id).first()

def persons_displayNames(session, userid):
  return session.query(Person).filter(Person.owner_id == userid).all()
    
def createPerson(session, isPrimary, displayName, profile, userid):
  try:
    p = Person(isPrimary, displayName, profile, userid, datetime.now())
    session.add(p)
    session.commit()
    return p

  except sqlalchemy.exc.IntegrityError, e:
    session.rollback()
    raise ValueError("Error while creating person (%s)" % e)

def user(session, uid):
  return session.query(User).filter(User.id == uid).first()

def createUser(session, ):
  try:
    u = User()
    session.add(u)
    session.commit()
    return u

  except sqlalchemy.exc.IntegrityError, e:
    session.rollback()
    raise ValueError("Error while creating user (%s)" % e)

def identity(session, identifier): # note that this could return more than one, e.g. if two users have claimed the same identity?
  return session.query(Identity).filter(Identity.identifier == identifier).all()
