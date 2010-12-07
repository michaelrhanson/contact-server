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
 *   Michael Hanson <mhanson@mozilla.com>
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

var gPerson = null;
var gContainer;
var gDocuments;

const CONTACT_CARD = 1;
const DATA_SOURCES = 2;

var gDisplayMode = CONTACT_CARD;

function createDiv(clazz)
{
	var aDiv = document.createElementNS("http://www.w3.org/1999/xhtml", "div");
	aDiv.setAttribute("class", clazz);
  return aDiv;
}

function createSpan(clazz, text)
{
	var aDiv = document.createElementNS("http://www.w3.org/1999/xhtml", "span");
	aDiv.setAttribute("class", clazz);
  if (text) aDiv.appendChild(document.createTextNode(text));
  return aDiv;
}

function createElem(type, clazz)
{
	var anElem = document.createElementNS("http://www.w3.org/1999/xhtml", type);
	if (clazz) anElem.setAttribute("class", clazz);
  return anElem;
}

function renderTypeValueList(title, objectType, list, options)
{
  var itemsDiv = createDiv("vlist");
  itemsDiv.setAttribute("id", objectType + "s");
  var titleDiv = createDiv("vlist_title");
  titleDiv.setAttribute("id", objectType + "stitle");
//  titleDiv.appendChild(document.createTextNode(title + ":"));
  itemsDiv.appendChild(titleDiv);

  var already = {};
  var count = 0;
  var itemContainer = itemsDiv; // could be reassigned for overflow
  for (var i=0;i<list.length;i++) {
    var item = list[i];
    var ctype= item["content-type"];
    if (ctype != undefined) {
      if (ctype == "text/html" || ctype == "application/atom+xml" || ctype == "text/plain") { // what about rdf+xml?  Google serves FOAF like that.  Hrm.
      } else {
        continue; // skip it.
      }
    }
    var value = item.value;
    if (options && options.itemRender) {
      value = options.itemRender(item);
      if (value == null) continue;
    }
    if (options && options.skipTypeList) {
      if (options.skipTypeList.indexOf(item.type) >= 0) continue;
    }
    if (options && options.skipPathSubstringList) {
      if (options.skipPathSubstringList.some(function(e) {return item.value.indexOf(e) >= 0})) continue;
    }

    // Normalize trailing slash for duplicate check
    var alreadyKey = value;
    if (alreadyKey.length > 0 && alreadyKey[alreadyKey.length - 1] == '/') alreadyKey = alreadyKey.substring(0, alreadyKey.length - 1);
    if (already[alreadyKey] != undefined) continue;
    already[alreadyKey] = 1;

    // Begin disclosure box, if needed...
    count++;
    if (options && options.hideLongList && (count == 6 || (options.longListCount && count > options.longListCount)) && !gOverflowRevealedMap[objectType]) {
      var disclosureDiv = createDiv("item_overflow");
      disclosureDiv.setAttribute("id", objectType + "overflow");
      disclosureDiv.style.display = 'none';
      itemsDiv.appendChild(disclosureDiv);
      itemContainer = disclosureDiv;
    }

    var itemDiv = createDiv("item");
    var itemTypeDiv = createDiv("type");
    var itemValueDiv = createDiv("value");
    if (item.type) {
      itemTypeDiv.appendChild(document.createTextNode(item.type));
    }

    var favicon= null;
    if (options && options.includeFavicon) {
      // TODO implement me
      if (false && favicon) {
        var faviconImg = createElem("img");
        faviconImg.setAttribute("src", favicon.spec);
        faviconImg.setAttribute("class", "valuefavicon");
        itemValueDiv.appendChild(faviconImg);
      }
    }
    if (options && options.linkify) {
      var link = createElem("a");
      if (options.onclick) {
        link.setAttribute("onclick", "openURL('"+value+"')");
        link.setAttribute("href", "javascript:void(null)");
      } else {
        link.setAttribute("href", value);
        link.setAttribute("target", "_blank");
      }
      
      if (item.title) {
        link.appendChild(document.createTextNode(item.title));
      } else {
        if (false && options.useHistoryTitles) {
          // TODO implement me
          var theURI = IO_SERVICE.newURI(item.value, null, null);
          var title = HISTORY_SERVICE.getPageTitle(theURI);
          if (title && title.length > 0 && title[0] != '/') {
            link.appendChild(document.createTextNode(title));        
          } else {
            link.appendChild(document.createTextNode(value));        
          }
        }
        else
        {
          link.appendChild(document.createTextNode(value));
        }
      }
      itemValueDiv.appendChild(link);
    } else if (options && options.linkToURL) {
      var link = createElem("a");
      if (options.onclick) {
        link.setAttribute("onclick", "openURL('"+options.linkToURL +escape(value)+"')");
        link.setAttribute("href", "javascript:void(null)");
      } else {
        link.setAttribute("href", options.linkToURL + escape(value));
        link.setAttribute("target", "_blank");
      }
      link.appendChild(document.createTextNode(value));
      itemValueDiv.appendChild(link);    
    } else {
      itemValueDiv.appendChild(document.createTextNode(item.value));
    }
    itemDiv.appendChild(itemTypeDiv);
    itemDiv.appendChild(itemValueDiv);
    itemContainer.appendChild(itemDiv);
  }
  if (options && options.hideLongList && count > 6 && !gOverflowRevealedMap[objectType]) {
    var link = createElem("a");
    link.setAttribute("class", "item_overflow_link");
    link.setAttribute("id", objectType + "overflowlink");
    link.setAttribute("onclick", "revealOverflow('" + objectType + "')");
    link.appendChild(document.createTextNode("Show " + (count-5) + " more..."));
    itemsDiv.appendChild(link);
  }
  return itemsDiv;
}

function renderPhotoList(title, objectType, list, options)
{
  var itemsDiv = createDiv("vlist");
  itemsDiv.setAttribute("id", objectType + "s");
  var titleDiv = createDiv("vlist_title");
  titleDiv.setAttribute("id", objectType + "stitle");
//  titleDiv.appendChild(document.createTextNode(title + ":"));
  itemsDiv.appendChild(titleDiv);

  var listContainer = itemsDiv;
  if (!gOverflowRevealedMap[objectType]) {
    var disclosureDiv = createDiv("item_overflow");
    disclosureDiv.setAttribute("id", objectType + "overflow");
    disclosureDiv.style.display = 'none';
    itemsDiv.appendChild(disclosureDiv);
    listContainer = disclosureDiv;

    var link = createElem("a");
    link.setAttribute("class", "item_overflow_link");
    link.setAttribute("id", objectType + "overflowlink");
    link.setAttribute("onclick", "revealOverflow('" + objectType + "')");
    link.appendChild(document.createTextNode("Show " + (list.length) + " photos..."));
    itemsDiv.appendChild(link);
  }
  
  var already = {};
  var itemContainer = itemsDiv; // could be reassigned for overflow
  var itemList = createElem("ul");
  itemList.setAttribute("class", "photolist");
  listContainer.appendChild(itemList);

  for (var i=0;i<list.length;i++) {
    var item = list[i];

    if (already[item.type + item.value] != undefined) continue;
    already[item.type + item.value] = 1;

    var theItem = createElem("li");
    var theImg = createElem("img");
    theImg.setAttribute("src", item.value);
    theImg.setAttribute("class", "listedPhoto");
    theItem.appendChild(theImg);
    itemList.appendChild(theItem);
  }
  return itemsDiv;
}


var gOverflowRevealedMap = {};
function revealOverflow(objectType)
{
  document.getElementById(objectType + "overflow").style.display='block';
  document.getElementById(objectType + "overflowlink").style.display='none';
  gOverflowRevealedMap[objectType] = 1;
  
}

function renderPerson()
{  
  gContainer.innerHTML = "working!";

  try {
    var personBox = createDiv("person vcard contact");
    personBox.setAttribute("id", "person");
    
    var controls = createDiv("displaymode");
    var link = createElem("a");
    controls.appendChild(link);
    personBox.appendChild(controls);
    
    switch (gDisplayMode) {
      case CONTACT_CARD:
        renderContactCard(personBox);
        link.setAttribute("onclick", "setDisplayMode(" + DATA_SOURCES +")");
        link.appendChild(document.createTextNode("View data sources"));
        break;
      case DATA_SOURCES:
        renderDataSources(personBox);
        link.setAttribute("onclick", "setDisplayMode(" + CONTACT_CARD +")");
        link.appendChild(document.createTextNode("Return to summary view"));
        break;
    }

    gContainer.innerHTML = "";
    gContainer.appendChild(personBox);
  } catch (e) {
    gContainer.innerHTML = "Uh oh, something went wrong! " + e;
    throw e;
  }
}

function setDisplayMode(mode)
{
  gDisplayMode = mode;
  renderPerson();
}

function renderContactCard(personBox)
{    
  var photos = getProperty(gPerson, "photos");
  if (photos) {
    var photoBox = createDiv("photo");
    var photoImg = createElem("img");
    photoImg.setAttribute("src", photos[0].value);
    photoImg.setAttribute("class", "profilePhoto");
    photoBox.appendChild(photoImg);
    personBox.appendChild(photoBox);
  }

  var dN = getProperty(gPerson, "displayName");
  if (dN) {
    var displayNameDiv = createDiv("displayName fn");
    displayNameDiv.appendChild(document.createTextNode(dN));
    personBox.appendChild(displayNameDiv);
    document.title = dN;

    var orgs = getProperty(gPerson, "organizations");
    if (orgs && orgs.length > 0) {
      var orgDiv = createDiv("org");
      var org = orgs[0];
      if (org.title) {
        orgDiv.appendChild(createSpan("title", org.title));
        if (org.name) orgDiv.appendChild(document.createTextNode(", "));
      }
      if (org.name) {
        orgDiv.appendChild(createSpan("summary", org.name)); 
      }
      displayNameDiv.appendChild(orgDiv);
    }
  }
  
  renderContactMethods(gPerson, personBox);
  renderContentLinks(gPerson, personBox);
}

function renderContactMethods(person, personBox)
{
  var photos = getProperty(gPerson, "photos");
  var contactBox = createDiv("contactMethods");
  var any = false;

  var heading = createDiv("subsecHead");
  heading.appendChild(document.createTextNode("Details:"));
  contactBox.appendChild(heading);
  
  var emails = getProperty(person, "emails");
  if (emails) {
    any = true;
    contactBox.appendChild(renderTypeValueList("Email Addresses", "email", emails, {linkToURL:"mailto:",onclick:true}));
  }
  var phones = getProperty(person, "phoneNumbers");
  if (phones) {
    any = true;
    contactBox.appendChild(renderTypeValueList("Phone Numbers", "phone", phones, {linkToURL:"callto:",onclick:true}));
  }
  var locations = getProperty(person, "location");
  if (locations) {
    any = true;
    contactBox.appendChild(renderTypeValueList("Locations", "location", locations, 
      {linkToURL:"http://maps.google.com/maps?q=", hideLongList:true, longListCount:1}));
  }

  var addresses = getProperty(person, "addresses");
  if (addresses) {
    any = true;
    contactBox.appendChild(renderTypeValueList("Addresses", "adr", addresses, {itemRender: function addrRender(item) {
      var val = "";
      if (item.streetAddress) {
        val += item.streetAddress;
        val += " ";
      }
      if (item.locality) {
        val += item.locality;
      }
      if (item.region) {// handle "city, ST" convention - TODO is this appropriate for non-US locales?
        if (val.length > 0) val += ", ";
        val += item.region;
      } 
      if (val.length > 0) val += " ";
      
      if (item.postalCode) {
        val += item.postalCode;
        val += " ";
      }
      if (item.country) {
        val += item.country;
        val += " ";
      }
      // remove dupes from locations
      if (locations && locations.some(function(e) {return (e.value == val.trim());})) return null;
      if (val.length == 0 && item.value) return item.value;
      return val;
     }, linkToURL:"http://maps.google.com/maps?q="}));
  }
  var birthday = getProperty(person, "birthday");
  if (birthday) {
    any = true;  
    contactBox.appendChild(renderTypeValueList("Birthday", "url", [{type:"Birthday", value:birthday}]));
  }

  if (photos && photos.length > 1) {
    any = true;
    contactBox.appendChild(renderPhotoList("Photos", "photos", photos));
  }
  
  if (any) {
    personBox.appendChild(contactBox);
  }
}

function renderContentLinks(person, personBox)
{
  var contentBox = createDiv("content");
  var any = false;

  var heading = createDiv("subsecHead");
  heading.appendChild(document.createTextNode("Content:"));
  contentBox.appendChild(heading);

  var urls = getProperty(person, "urls");
  if (urls) {
    urls = selectTopLevelUrls(urls);
    any = true;
    contentBox.appendChild(renderTypeValueList("Links", "url", urls, 
      {includeFavicon:true, linkify:true, hideLongList:false, skipTypeList:["data"],
       skipPathSubstringList:["/friend", "/contacts"]
      }
    ));
  }
  var notes = getProperty(person, "notes");
  if (notes) {
    any = true;
    contentBox.appendChild(renderTypeValueList("Notes", "note", notes));
  }
  if (any) {
    personBox.appendChild(contentBox);
  }

}


function formatDate(dateStr)
{
  if (!dateStr) return "null";
  
  var now = new Date();
  var then = new Date(dateStr);

  if (then.getDate() != now.getDate())
  {
     var dayDelta = (new Date().getTime() - then.getTime() ) / 1000 / 60 / 60 / 24 // hours
     if (dayDelta < 2) str = "yesterday";
     else if (dayDelta < 7) str = Math.floor(dayDelta) + " days ago";
     else if (dayDelta < 14) str = "last week";
     else if (dayDelta < 30) str = Math.floor(dayDelta) + " days ago";
     else str = Math.floor(dayDelta /30)  + " month" + ((dayDelta/30>2)?"s":"") + " ago";
  } else {
      var str;
      var hrs = then.getHours();
      var mins = then.getMinutes();
      
      var hr = Math.floor(Math.floor(hrs) % 12);
      if (hr == 0) hr =12;
      var mins = Math.floor(mins);
      str = hr + ":" + (mins < 10 ? "0" : "") + Math.floor(mins) + " " + (hrs >= 12 ? "P.M." : "A.M.");
  }
  return str;
}


function renderDataSources(personBox)
{
  var svcbox = createDiv("servicedetail");
  for (var aService in gPerson.documents)
  {
    var aDoc = gPerson.documents[aService];

    var header = createDiv("header");
    header.innerHTML = "Loaded from " + aService;
    svcbox.appendChild(header);
    traverseRender(aDoc, svcbox);
  }
  personBox.appendChild(svcbox);
}

function traverseRender(anObject, container)
{
  for (var aKey in anObject)
  {
    if (isArray(anObject[aKey]))
    {
      var count = 1;
      var subhead = createDiv("subhead");
      subhead.appendChild(document.createTextNode(aKey));
      for (var i=0;i<anObject[aKey].length;i++) 
      {
        var anItem = anObject[aKey][i];
        if (typeof anItem == "string") 
        {
          var item = createDiv("item");
          var slot = createDiv("slot");
          var label = createDiv("svcdetaillabel");
          var value = createDiv("svcdetailvalue");
          value.appendChild(document.createTextNode(anItem));
          slot.appendChild(label);
          slot.appendChild(value);
          item.appendChild(slot);
          subhead.appendChild(item);
        }
        else if (anItem.hasOwnProperty("type") && anItem.hasOwnProperty("value"))
        {
          var item = createDiv("item");
          var slot = createDiv("slot");
          var label = createDiv("svcdetaillabel");
          var value = createDiv("svcdetailvalue");
          label.appendChild(document.createTextNode(anItem.type));
          value.appendChild(document.createTextNode(anItem.value));
          slot.appendChild(label);
          slot.appendChild(value);
          item.appendChild(slot);
          if (anItem.rel && anItem.rel != anItem.type) {
            var rel = createDiv("svcdetailvaluerel");
            rel.appendChild(document.createTextNode("rel: " + anItem.rel));
            value.appendChild(rel);
          }

          /* display full metadata: sometimes useful for debugging
          for (var aSlot in anItem)
          {
            var slot = createDiv("svcdetailvaluerel");
            slot.appendChild(document.createTextNode(aSlot +": " + anItem[aSlot]));
            value.appendChild(slot);          
          }
          */


          subhead.appendChild(item);
        }
        else if (anItem.hasOwnProperty("domain")) // specialcase for accounts
        {
          var item = createDiv("item");
          var slot = createDiv("slot");
          var label = createDiv("svcdetaillabel");
          var value = createDiv("svcdetailvalue");
          label.appendChild(document.createTextNode(anItem.domain));
          var username = anItem.username;
          var userid = anItem.userid;
          var un;
          if (username && userid) {
            un = username + " (" + userid + ")";
          } else if (username) un = username;
          else if (userid) un = userid;
          
          if (un) {
            value.appendChild(document.createTextNode(un));
          } else {
            value.appendChild(document.createTextNode("(No username)"));
          }
          slot.appendChild(label);
          slot.appendChild(value);
          item.appendChild(slot);
          subhead.appendChild(item);
        }
        else 
        {
          // generic item; use 'name' if it is present
          var item = createDiv("counteditem");
          
          var textLabel;
          /*if (anItem.name) textLabel = anItem.name;
          else */textLabel = "Item #" + count;

          var slot = createDiv("slot");
          var label = createDiv("svccountedlabel");
          label.appendChild(document.createTextNode(textLabel));
          slot.appendChild(label);
          item.appendChild(slot);

          for (var aSlot in anItem)
          {
            var slot = createDiv("slot");
            var label = createDiv("svcdetaillabel");
            var value = createDiv("svcdetailvalue");
            label.appendChild(document.createTextNode(aSlot));
            value.appendChild(document.createTextNode(anItem[aSlot]));
            slot.appendChild(label);
            slot.appendChild(value);
            item.appendChild(slot);
          }
          subhead.appendChild(item);
          count = count + 1;
        }
      }
      container.appendChild(subhead);
    }
    else if (typeof anObject[aKey] == 'object') 
    {
      var subhead = createDiv("subhead");
      subhead.appendChild(document.createTextNode(aKey));
      var nestbox = createDiv("nestbox");
      subhead.appendChild(nestbox);
      traverseRender(anObject[aKey], nestbox);
      container.appendChild(subhead);
    }
    else
    {
      var slot = createDiv("slot");
      var label = createDiv("svcdetaillabel");
      var value = createDiv("svcdetailvalue");
      
      if (aKey == "_refreshDate") {
        var dateStr = formatDate(new Date(anObject[aKey]))

        label.appendChild(document.createTextNode("Refreshed at"));
        value.appendChild(document.createTextNode(dateStr))
      } else {
        label.appendChild(document.createTextNode(aKey));
        value.appendChild(document.createTextNode(anObject[aKey]));
      }
      slot.appendChild(label);
      slot.appendChild(value);
      container.appendChild(slot);
    }
  }
}




var UNIQUE_URLS = ["http://www.facebook.com/"];
function selectTopLevelUrls(urls)
{
  var tmp = [];
  
  // if it's a unique URL, take the shortest one.  This is, admittedly,
  // a hack to cause the vanity Facebook URL to come up first.
  
  // otherwise, if any URLs are prefixes of other URLs in the list,
  // take the shorter one.
  
  var shortMap = {};
  
  for (var i=0;i<urls.length;i++) {
    var u = urls[i];
    var wasAUnique = false;
    for (var j=0;j<UNIQUE_URLS.length;j++) {
      var unique = UNIQUE_URLS[j];
      if (u.value.indexOf(unique) == 0) {
        if (!shortMap[unique]) shortMap[unique] = u;
        else {
          if (u.value.length < shortMap[unique].value.length) {
            shortMap[unique] = u;
          }
        }
        wasAUnique = true;
      }
    }
    if (!wasAUnique) {
      tmp.push(u);
    }
  }
  
  var ret = [];
  for (u in shortMap) {
    ret.push(shortMap[u]);
  }
  ret = ret.concat(tmp);
/*
  for each (var u in urls) {
    var matched = false;
    for each (var r in ret) {
      if (u.value.indexOf(r.value) == 0) {matched = true;break;}
    }
    if (!matched) ret.push(u);
  }*/
  return ret;
}

function getProperty(aPerson, aProperty) {
  var terms = aProperty.split('/');
  if (terms.length == 1) { // easy case
    return searchCollection(aProperty, aPerson.documents, "");
  }
  
  var currentSet = [];
  for (var d=0;d<aPerson.documents.length;d++) currentSet.push(aPerson.documents[d]);
  var currentPrefix = "";
  for (var i=0;i<terms.length;i++) 
  {
    var term = terms[i];
    if (!isArray(currentSet)) currentSet = [currentSet];
    currentSet = searchCollection(term, currentSet, currentPrefix);
    if (currentSet == null) break;
    currentPrefix = currentPrefix + "/" + term;
  }
  return currentSet;
}

function searchCollection(property, collection, propertyNameContext)
{
  var returnValue = null;
  for (anIndex in collection)
  {
    var anObject = collection[anIndex];
    if (anObject[property]) {
      if (returnValue) {
        returnValue = mergeFields(propertyNameContext + property, returnValue, anObject[property]);
      } else {
        if (isArray(anObject[property])) {
          // need to make a shallow copy of the array, so we can merge into it later...
          returnValue = anObject[property].slice(0);
        } else {
          returnValue = anObject[property];
        }
      }
    }
  }
  return returnValue;  
}

// Given two values, returns their union according to the rules of <fieldName>.
function mergeFields(fieldName, currentValue, newValue) {
  // TODO: We should be prescriptive about cardinality here.
  // For now we just merge lists.
  if (isArray(currentValue))
  {
    if (isArray(newValue))
    {
      // two arrays, and we need to check for object equality...
      for (index in newValue) {
        var newObj = newValue[index];

        // Do any of the objects in newValue match newObj?
        var equalObjs = currentValue.filter(function(item, idx, array) 
        {
          if (item.hasOwnProperty("type") && item.hasOwnProperty("value") &&
              newObj.hasOwnProperty("type") && newObj.hasOwnProperty("value"))
          {
            // special-case for type-value pairs.  If the value is identical,
            // we may want to discard one of the types -- unless they have
            // different rels.
            if (newObj.value == item.value) {
              if (newObj.type == item.type) {
                if (newObj.rel && item.rel) {
                  return (newObj['rel'] == item.rel);
                } else {
                  return true;
                }
              } else if (newObj.type == "internet") {// gross hack for VCard email
                newObj.type = item.type;
                return true;
              } else if (item.type == "internet") {
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
          currentValue.push(newObj);
        } else {
          // yes, merge values into equalObjs[0]...
          this._mergeObject(equalObjs[0], newObj);
        }
      }
    }
    else
    {
      console.log("Cardinality error: property " + fieldName + " is a list in one document, and a field in another");
    }
  }
  // If it's not a list, first one wins.  TODO: Do better than that.
  return currentValue;
}

function mergeObject(to, from) {
  // existing values win.
  for (var key in from) {
    if (!to[key]) to[key] = from[key];
  }
}

function isArray(obj) {
  return obj != null && obj.constructor.toString() == Array;
}

function htmlescape(html) {
	if (!html) return html;
	if (!html.replace) return html;
  
  return html.
    replace(/&/gmi, '&amp;').
    replace(/"/gmi, '&quot;').
    replace(/>/gmi, '&gt;').
    replace(/</gmi, '&lt;')
}

