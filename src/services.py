import json
import logging

class ContactServiceFactory(object):
  def __init__(self):
    self.services = []
  
  # A ContactService must response to the "svc.lookup(identifier, result, user)"
  # method; when it has finished, it must call the result.reportServiceResult()
  # method.  It must also have a getName() method.
  def registerService(self, service):
    self.services.append(service)
  
  def getServicesForIdentifier(self, identifier):
    # The identifier is data that arrived off the internet,
    # so it could be just about anything.
    
    # We could look for email address, URL, md5 of something;
    # and truncate our list of services based on a prefilter -    
    # but for now we always return the entire thing.
    return self.services

class Result(object):
  def __init__(self, completionCallback):
    self.completionCallback = completionCallback
    self.pending = []
    self.result = {}    
  
  def addPendingService(self, svc):
    self.pending.append(svc.getName())
    logging.info("PEnding is %s" % self.pending)
  
  def anyPendingServices(self):
    return len(self.pending) > 0
  
  def reportServiceResult(self, svc, result):
    # Add results to what we've got so far
    if result:
      self.result[svc.getName()] = result

    # And report completion, if we're done
    logging.info("Removing %s - pending is %s" % (svc.getName(), self.pending))
    self.pending.remove(svc.getName())
    logging.info("PEnding is %s" % self.pending)

    if len(self.pending) == 0:
      self.completionCallback()
    logging.info("Got lookup result for %s; %d items still pending" % (svc.getName(), len(self.pending)))
    
  def renderJSON(self):
    logging.error("Rendering %s " % self.result)
    return json.dumps(self.result)


Factory = ContactServiceFactory()
