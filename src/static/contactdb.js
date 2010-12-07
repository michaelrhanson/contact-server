	/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is People.
 *
 * The Initial Developer of the Original Code is Mozilla.
 * Portions created by the Initial Developer are Copyright (C) 2009
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *  Dan Mills <thunder@mozilla.com>
 *  Justin Dolske <dolske@mozilla.com>
 *  Michael Hanson <mhanson@mozilla.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */


/** Global array of all contacts */
var gContacts = [];

function searchForEmail(emailValue)
{
  var result = [];
  for (var i=0;i<gContacts.length;i++) 
  {
    var emails = getProperty(gContacts[i], "emails");
    if (emails)
    {
      for (var j=0;j<emails.length;j++)
      {
        if (emails[j].value && emails[j].value == emailValue)
        {
          result.push(gContacts[i]);
          break;
        }
      }
    }
  }
  return result;
}

function searchForDisplayName(name)
{
  var result = [];
  for (var i=0;i<gContacts.length;i++) 
  {
    var dn = getProperty(gContacts[i], "displayName");
    if (dn && dn == name)
    {
      result.push(gContacts[i]);
    }
  }
  return result;
}

/** Given an input document (not a full contact!), find 
 * all contact that have the same emails. */
function searchForMergeTarget(inputDoc) {

  if (inputDoc.emails && inputDoc.emails.length > 0) {
    for (var i=0;i<inputDoc.emails.length;i++) 
    {
      if (inputDoc.emails[i].value) {
        var match = searchForEmail(inputDoc.emails[i].value);
        
        // First one wins, for now.
        if (match && match.length > 0) {
          return match[0];
        }
      }
    }
  }
  
  // Now try full name match:
  if (inputDoc.displayName && inputDoc.displayName != "undefined" && inputDoc.displayName != "null") {
    var match = searchForDisplayName(inputDoc.displayName);
    
    // Any match is a win.
    if (match && match.length > 0) {
      return match[0];
    }
  }
  
  return null;
}


function addContactDocument(inputDocument, inputDocumentServiceID)
{
  var theContact;
  mergeTarget = searchForMergeTarget(inputDocument);
  if (mergeTarget) {
    if (mergeTarget.documents[inputDocumentServiceID]) {
      mergeDocuments(mergeTarget.documents[inputDocumentServiceID], inputDocument);
    } else {
      mergeTarget.documents[inputDocumentServiceID] = inputDocument;
    }
    theContact = mergeTarget;
  } else {
    var docs = {};
    docs[inputDocumentServiceID] = inputDocument;
    theContact = { documents:docs } ;
    gContacts.push( theContact );
  }
  
  synthesizeFields(theContact);
}

function addDocumentToContact(targetContact, inputDocument, inputDocumentServiceID)
{
  targetContact.documents[inputDocumentServiceID] = inputDocument;
  synthesizeFields(targetContact);
}

function mergeDocuments(destDocument, sourceDocument) {
  // TODO: Need to get more sensible approach to cardinality.
  // e.g. What if we get two displayNames?
  
  for (var attr in sourceDocument) {
    if (sourceDocument.hasOwnProperty(attr)) {
      var val = sourceDocument[attr];
      
      if (!destDocument.hasOwnProperty(attr)) {
        // TODO right now, first one wins.  Need a more sensible approach.
        destDocument[attr] = val;
      } 
      else
      {
        if (isArray(val))
        {
          if (isArray(destDocument[attr]))
          {
            // two arrays, and we need to check for object equality...
            for (index in val) {
              var newObj = val[index];

              // Are any of these objects equal?
              var equalObjs = destDocument[attr].filter(function(item, idx, array) {
                if (item.hasOwnProperty("type") && item.hasOwnProperty("value") &&
                    newObj.hasOwnProperty("type") && newObj.hasOwnProperty("value"))
                {
                  // special-case for type-value pairs.  If the value is identical,
                  // we may want to discard one of the types -- unless they have
                  // different rels.
                  if (newObj.value == item.value) {
                    if (newObj.type == item.type) {
                      if (newObj['rel'] == item.rel) {
                        return true;
                      }
                    } else if (newObj.type == "internet" || newObj.type == "unlabeled") {// gross hack for Google, Yahoo, etc.
                      newObj.type = item.type;
                      return true;
                    } else if (item.type == "internet" || item.type == "unlabeled") {
                      item.type = newObj.type;
                      return true;
                    } else {
                      // Could, potentially, combine the types?
                      return false;
                    }
                  }
                }
                else
                {
                  return objectEquals(item, newObj)}
                }
              );
              if (equalObjs.length == 0) { // no match, go ahead...
                destDocument[attr].push(val[index]);
              }
            }
          }
          else
          {
            // log oddity: one was list, one not
          }
        }
      }
    }
  }
}

function synthesizeFields(contact)
{
  if (contact.documents.synthesized) 
    delete contact.documents.synthesized;
  
  var name = getProperty(contact, "name");
  var synth;
  if (!name) {
    var displayName = getProperty(contact, "displayName");
    if (displayName) {
      name = {};
      var nameParts = displayName.split(" ");
      if (nameParts.length > 1) {
        name.familyName = nameParts[nameParts.length - 1];
        name.givenName = nameParts.slice(0, nameParts.length - 1).join(" ");
      } else {
        name.familyName = displayName;
      }
      synth = {};
      synth.name = name;
    }
  }
  if (synth) 
    contact.documents.synthesized = synth;
}

function sortContacts()
{
  gContacts.sort(function(a, b) {
    try {
      var aN = getProperty(a, "name");
      var bN = getProperty(b, "name");

      if (aN && bN && aN.familyName && bN.familyName) {
        var ret= aN.familyName.localeCompare(bN.familyName);
        if (ret == 0) {
          if (aN.givenName && bN.givenName) {
           return aN.givenName.localeCompare(bN.givenName);
          } else if (aN.givenName) {
            return -1;
          } else if (bN.givenName) {
            return 1;
          } else {
            return 0;
          }
        } else {
          return ret;
        }
      } else if (aN && aN.familyName) {
        return -1;
      } else if (bN && bN.familyName) {
        return 1;
      }
      
      var aDN = getProperty(a, "displayName");
      var bDN = getProperty(b, "displayName");
      
      if (aDN && bDN) {
         return aDN.localeCompare(bDN);
      } else if (aDN) {
        return -1;
      } else if (bDN) {
        return 1;
      } else {
        return 0;
      }
    } catch (e) {
      return 0;
    }
  });
}

function objectEquals(obj1, obj2) {
    for (var i in obj1) {
        if (obj1.hasOwnProperty(i)) {
            if (!obj2.hasOwnProperty(i)) return false;
            if (obj1[i] != obj2[i]) return false;
        }
    }
    for (var i in obj2) {
        if (obj2.hasOwnProperty(i)) {
            if (!obj1.hasOwnProperty(i)) return false;
            if (obj1[i] != obj2[i]) return false;
        }
    }
    return true;
}