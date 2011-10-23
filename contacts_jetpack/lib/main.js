var {Cc, Ci, Cu, Cm} = require("chrome");
const tabs = require("tabs");
const data = require("self").data;

/* We pagemod the Contacts page, so these capabilities are only available to that one */
var pageMod = require("page-mod");
pageMod.PageMod({
  include: "*.mozillalabs.com",
  contentScriptWhen: "end",
  contentScriptFile: data.url("maclocalsource.js"),
  onAttach: function onAttach(worker) {
  	worker.on('message', function(data) {
 		console.log("Mac Contacts Pagemod got message: " + data);
 		
 		if (data.cmd == "refresh") {
			 worker.postMessage({cmd:"refresh", contacts:getAllContacts()});
 		} else if (data.cmd == "getactivity") {
 			var target = data.target;
 			if (target.emails) {
 				var em = [];
 				for (var i in target.emails) em.push(target.emails[i].value);
 				var activity = getActivity(em);
	 			worker.postMessage({cmd:"getactivity", activity:activity});
	 		}
 		} else if (data.cmd == "getrecentactivity") {
 			getRecentActivity(function(result) {
 				worker.postMessage({cmd:"getrecentactivity", activity:result});
 			});
 		}
      }
    );
  }
});


console.log("The Contacts add-on is running.");

try {
	var c = {};
	Cu.import("resource://gre/modules/ctypes.jsm", c);
	var ctypes = c.ctypes;
	var lib = ctypes.open("/System/Library/Frameworks/AddressBook.framework/Versions/A/AddressBook");
	var cflib = ctypes.open("/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation");
	var cslib = ctypes.open("/System/Library/Frameworks/CoreServices.framework/Versions/A/CoreServices");

	var CFRange = ctypes.StructType("CFRange", 
		[ {'location': ctypes.int64_t},   // signed long
		  {'length': ctypes.int64_t} ]);  // signed long

	var ABSGetSharedAddressBook = lib.declare(
			"ABGetSharedAddressBook",
			ctypes.default_abi,
			ctypes.voidptr_t); // return AddressBook

	var ABCopyArrayOfAllPeople = lib.declare(
			"ABCopyArrayOfAllPeople",
			ctypes.default_abi,
			ctypes.voidptr_t, // return CFArrayRef
			ctypes.voidptr_t); // Takes AddressBook

	var ABGetMe = lib.declare(
			"ABGetMe",
			ctypes.default_abi,
			ctypes.voidptr_t, // return ABPersonRef
			ctypes.voidptr_t);// takes AddressBook

	var ABMultiValueCount = lib.declare(
			"ABMultiValueCount",
			ctypes.default_abi,
			ctypes.int, // return int
			ctypes.voidptr_t);// takes ABMultiValueRef

	var ABMultiValueCopyLabelAtIndex = lib.declare(
			"ABMultiValueCopyLabelAtIndex",
			ctypes.default_abi,
			ctypes.voidptr_t, // return CFStringRef
			ctypes.voidptr_t,// takes ABMultiValueRef
			ctypes.int) // takes int

	var ABMultiValueCopyValueAtIndex = lib.declare(
			"ABMultiValueCopyValueAtIndex",
			ctypes.default_abi,
			ctypes.voidptr_t, // return CFStringRef
			ctypes.voidptr_t,// takes ABMultiValueRef
			ctypes.int) // takes int

	var CharPtr = ctypes.PointerType(ctypes.char);
	var JSCharPtr = ctypes.PointerType(ctypes.jschar);

	var ABRecordCopyValue = lib.declare(
			"ABRecordCopyValue",
			ctypes.default_abi,
			JSCharPtr, // voidptr_t, // returns CFTypeRef 
			ctypes.voidptr_t, // ABPersonRef
			ctypes.voidptr_t);// CFStringRef (a kAB constant)

	var ABPersonCopyImageData = lib.declare(
			"ABPersonCopyImageData",
			ctypes.default_abi,
			ctypes.voidptr_t, // voidptr_t, // returns CFDataRef
			ctypes.voidptr_t);// ABPersonRef

	var CFDataGetBytes = cflib.declare(
			"CFDataGetBytes",
			ctypes.default_abi,
			ctypes.int32_t, // returns CFIndex
			ctypes.voidptr_t, // takes CFDataRef
			CFRange, // CFRange
			ctypes.voidptr_t); // buffer

	var CFDataGetBytePtr = cflib.declare(
			"CFDataGetBytePtr",
			ctypes.default_abi,
			ctypes.PointerType(ctypes.uint8_t), // voidptr_t, // returns voidptr
			ctypes.voidptr_t); // takes CFDataRef

	var CFDataGetLength = cflib.declare(
			"CFDataGetLength",
			ctypes.default_abi,
			ctypes.int32_t, // returns CFIndex
			ctypes.voidptr_t); // takes CFDataRef
	
	var CFStringGetLength = cflib.declare(
			"CFStringGetLength",
			ctypes.default_abi,
			ctypes.int32_t, // returns CFIndex
			ctypes.voidptr_t); // takes CFStringRef				

	/* 
	typedef struct {
	    CFIndex location;
	    CFIndex length;
	} CFRange; */
	
	// void CFStringGetCharacters(CFStringRef theString, CFRange range, UniChar *buffer);
	var CFStringGetCharacters = cflib.declare(
			"CFStringGetCharacters",
			ctypes.default_abi,
			ctypes.void_t, // returns CFIndex
			ctypes.voidptr_t, // CFStringRef
			CFRange, // range
			JSCharPtr);
	
	// UniChar CFStringGetCharacterAtIndex(CFStringRef theString, CFIndex idx);
	var CFStringGetCharacterAtIndex = cflib.declare(
			"CFStringGetCharacterAtIndex",
			ctypes.default_abi,
			ctypes.jschar, // returns CFIndex
			ctypes.voidptr_t, // CFStringRef
			ctypes.int); // idx

	// CFStringCreateWithCharacters
	var CFStringCreateWithCharacters = cflib.declare(
			"CFStringCreateWithCharacters",
			ctypes.default_abi,
			ctypes.voidptr_t, // returns CFStringRef			
			ctypes.voidptr_t, // Allocator
			JSCharPtr, // Unichar*
			ctypes.int); // length

	var CFArrayCreateMutable = cflib.declare(
			"CFArrayCreateMutable",
			ctypes.default_abi,
			ctypes.voidptr_t, // returns CFArrayRef
			ctypes.voidptr_t, // allocator
			ctypes.int, // capacity
			ctypes.voidptr_t); // callbacks

	var CFArraySetValueAtIndex = cflib.declare(
			"CFArraySetValueAtIndex",
			ctypes.default_abi,
			ctypes.void_t, // returns void
			ctypes.voidptr_t, // CFMutableArrayRef
			ctypes.int, // index
			ctypes.voidptr_t); // value

	var CFArrayGetCount = cflib.declare(
			"CFArrayGetCount",
			ctypes.default_abi,
			ctypes.int, // returns CFIndex
			ctypes.voidptr_t); // CFArrayRef

	var CFArrayGetValueAtIndex = cflib.declare(
			"CFArrayGetValueAtIndex",
			ctypes.default_abi,
			ctypes.voidptr_t, // returns CFValueRef
			ctypes.voidptr_t, // CFArrayRef
			ctypes.int); // idnex

	var CFDateGetAbsoluteTime = cflib.declare(
			"CFDateGetAbsoluteTime",
			ctypes.default_abi,
			ctypes.double, // returns CFTimeInterval, which is time since 00:00:00 1 January 2001
			ctypes.voidptr_t); // CFDateRef

	var CFDictionaryGetValue = cflib.declare(
			"CFDictionaryGetValue",
			ctypes.default_abi,
			ctypes.voidptr_t, // returns CFTypeRef
			ctypes.voidptr_t, // CFDictionaryRef
			ctypes.voidptr_t); // CFStringRef

	var CFNumberGetValue = cflib.declare(
			"CFNumberGetValue",
			ctypes.default_abi,
			ctypes.int, // returns Boolean
			ctypes.voidptr_t, // CFNumberRef
			ctypes.int, // CFNumberType
			ctypes.voidptr_t); // valuePtr
	var kCFNumberSInt32Type = 3; //http://developer.apple.com/library/mac/#documentation/CoreFoundation/Reference/CFNumberRef/Reference/reference.html
	
	var kABFirstNameProperty = lib.declare("kABFirstNameProperty", JSCharPtr);
	var kABLastNameProperty = lib.declare("kABLastNameProperty", JSCharPtr);

	var kABOrganizationProperty = lib.declare("kABOrganizationProperty", JSCharPtr);
	var kABJobTitleProperty = lib.declare("kABJobTitleProperty", JSCharPtr);
	var kABDepartmentProperty = lib.declare("kABDepartmentProperty", JSCharPtr);

	var kABEmailProperty = lib.declare("kABEmailProperty", JSCharPtr);
	
	var kABURLsProperty = lib.declare("kABURLsProperty", ctypes.voidptr_t);	
	var kABHomePageLabel = lib.declare("kABHomePageLabel", ctypes.voidptr_t);	
	
	var kABAddressProperty = lib.declare("kABAddressProperty", JSCharPtr);
	var kABAddressStreetKey = lib.declare("kABAddressStreetKey", JSCharPtr);
	var kABAddressCityKey = lib.declare("kABAddressCityKey", JSCharPtr);
	var kABAddressStateKey = lib.declare("kABAddressStateKey", JSCharPtr);
	var kABAddressZIPKey = lib.declare("kABAddressZIPKey", JSCharPtr);
	var kABAddressCountryKey = lib.declare("kABAddressCountryKey", JSCharPtr);
	var kABAddressCountryCodeKey = lib.declare("kABAddressCountryCodeKey", JSCharPtr);

	var kABBirthdayProperty = lib.declare("kABBirthdayProperty", JSCharPtr);
	var kABOtherDatesProperty = lib.declare("kABOtherDatesProperty", JSCharPtr);
	var kABAnniversaryLabel = lib.declare("kABAnniversaryLabel", JSCharPtr);

	var kABPersonFlags = lib.declare("kABPersonFlags", JSCharPtr); //  kABShowAsMask=000007; kABShowAsPerson=000000; kABShowAsCompany=000001
				// kABNameOrderingMask=000070; kABDefaultNameOrdering=000000; kABFirstNameFirst=000040; kABLastNameFirst=000020
	var kABPhoneProperty = lib.declare("kABPhoneProperty", JSCharPtr);

	var kABPhoneMobileLabel = lib.declare("kABPhoneMobileLabel", JSCharPtr);
	var kABPhoneMainLabel = lib.declare("kABPhoneMainLabel", JSCharPtr);
	var kABPhoneHomeFAXLabel = lib.declare("kABPhoneHomeFAXLabel", JSCharPtr);
	var kABPhoneWorkFAXLabel = lib.declare("kABPhoneWorkFAXLabel", JSCharPtr);
	var kABPhonePagerLabel = lib.declare("kABPhonePagerLabel", JSCharPtr);

	var kABAIMInstantProperty = lib.declare("kABAIMInstantProperty", JSCharPtr);
	var kABJabberInstantProperty = lib.declare("kABJabberInstantProperty", JSCharPtr);
	var kABMSNInstantProperty = lib.declare("kABMSNInstantProperty", JSCharPtr);
	var kABYahooInstantProperty = lib.declare("kABYahooInstantProperty", JSCharPtr);
	var kABICQInstantProperty = lib.declare("kABICQInstantProperty", JSCharPtr);
	
	var kABNoteProperty = lib.declare("kABNoteProperty", JSCharPtr);

	var kABMiddleNameProperty = lib.declare("kABMiddleNameProperty", JSCharPtr);
	var kABTitleProperty = lib.declare("kABTitleProperty", JSCharPtr);
	var kABSuffixProperty = lib.declare("kABSuffixProperty", JSCharPtr);
	
	var kABWorkLabel = lib.declare("kABWorkLabel", JSCharPtr);
	var kABHomeLabel = lib.declare("kABHomeLabel", JSCharPtr);
	var kABOtherLabel = lib.declare("kABOtherLabel", JSCharPtr);

	var kWorkLabel = convertCFString(kABWorkLabel);
	var kHomeLabel = convertCFString(kABHomeLabel);
	var kOtherLabel = convertCFString(kABOtherLabel);
	var kPhoneMobileLabel = convertCFString(kABPhoneMobileLabel);
	var kPhoneHomeFAXLabel = convertCFString(kABPhoneHomeFAXLabel);
	var kPhoneWorkFAXLabel = convertCFString(kABPhoneWorkFAXLabel);
	var kPhonePagerLabel = convertCFString(kABPhonePagerLabel);
	var kPhoneMainLabel = convertCFString(kABPhoneMainLabel);
	var kHomePageLabel = convertCFString(kABHomePageLabel);
	

	var MDQueryCreate = cslib.declare(
		"MDQueryCreate",
		ctypes.default_abi,
		ctypes.voidptr_t, // returns MDQueryRef
		ctypes.voidptr_t, // allocator
		ctypes.voidptr_t, // CFStringRef queryString
		ctypes.voidptr_t, // CFArrayRef valueListAttrs
		ctypes.voidptr_t) // CFArrayRef sortingAttrs

	var MDQueryExecute = cslib.declare(
		"MDQueryExecute",
		ctypes.default_abi,
		ctypes.int, // returns boolean
		ctypes.voidptr_t, // MDQueryRef theQuery
		ctypes.int); // CFOptionFlags

	var MDQueryGetResultCount = cslib.declare(
		"MDQueryGetResultCount",
		ctypes.default_abi,
		ctypes.int, // returns CFIndex
		ctypes.voidptr_t); // MDQueryRef theQuery

	var MDQueryGetResultAtIndex = cslib.declare(
		"MDQueryGetResultAtIndex",
		ctypes.default_abi,
		ctypes.voidptr_t, // returns void*
		ctypes.voidptr_t, // MDQueryRef
		ctypes.int); // index


	var MDQueryGetAttributeValueOfResultAtIndex = cslib.declare(
		"MDQueryGetAttributeValueOfResultAtIndex",
		ctypes.default_abi,
		ctypes.voidptr_t, // returns void*
		ctypes.voidptr_t, // MDQueryRef
		ctypes.voidptr_t, // CFStringRef name
		ctypes.int); // index

	var kMDItemPath = cslib.declare("kMDItemPath", JSCharPtr);
	var kMDItemContentCreationDate = cslib.declare("kMDItemContentCreationDate", JSCharPtr);
	var kMDItemFSName = cslib.declare("kMDItemFSName", JSCharPtr);
	var kMDItemDisplayName = cslib.declare("kMDItemDisplayName", JSCharPtr);
	var kMDItemAuthorEmailAddresses = cslib.declare("kMDItemAuthorEmailAddresses", JSCharPtr);	

} catch (e) {
	console.log(e);
	console.log(e.stack)
}

function deriveLabelFromString(aNativeLabel)
{
	if (aNativeLabel == kWorkLabel) {
		return "work";
	} else if (aNativeLabel ==kHomeLabel) {
		return "home";
	} else if (aNativeLabel ==kOtherLabel) {
		return "other";
	} else if (aNativeLabel ==kPhoneMobileLabel) {
		return "mobile";
	} else if (aNativeLabel ==kPhoneHomeFAXLabel) {
		return "home fax";
	} else if (aNativeLabel ==kPhoneWorkFAXLabel) {
		return "work fax";
	} else if (aNativeLabel ==kPhonePagerLabel) {
		return "pager";
	} else if (aNativeLabel ==kPhoneMainLabel) {
		return "main";
	} else if (aNativeLabel ==kHomePageLabel) {
		return "home page";
	} else {
    	return aNativeLabel;
	}
}

function getAllContacts()
{
	var addressBook = ABSGetSharedAddressBook();
	var allPeople = ABCopyArrayOfAllPeople(addressBook);
	var me = ABGetMe(addressBook);
	var allPeopleCount = CFArrayGetCount(allPeople);
	var contacts = [];
	for (var i=0;i<allPeopleCount;i++) {
		var person = CFArrayGetValueAtIndex(allPeople, i);
		
		var flags = ABRecordCopyValue(person, kABPersonFlags);
		var flagVal = new ctypes.int32_t()
		CFNumberGetValue(flags, kCFNumberSInt32Type, flagVal.address());
		if ((flagVal.value & 0x01) == 1) continue; // skip companies
		
		var aContact = {};
		var firstName = convertCFString(ABRecordCopyValue(person, kABFirstNameProperty));
		var lastName = convertCFString(ABRecordCopyValue(person, kABLastNameProperty));
		if (firstName) {
			if (!aContact.name) aContact.name = {};
			aContact.name.givenName = firstName;
		}
		if (lastName) {
			if (!aContact.name) aContact.name = {};
			aContact.name.familyName = lastName;
		}
		var emails = ABRecordCopyValue(person, kABEmailProperty);
		for (var j=0;j<ABMultiValueCount(emails);j++)
		{
			if (!aContact.emails) aContact.emails = [];
			nativeType = convertCFString(ABMultiValueCopyLabelAtIndex(emails, j));			
			aContact.emails.push( {
				value:convertCFString(ABMultiValueCopyValueAtIndex(emails, j)),
				type: deriveLabelFromString(nativeType)
			}); 
		}
		var org = convertCFString(ABRecordCopyValue(person, kABOrganizationProperty));
		var title = convertCFString(ABRecordCopyValue(person, kABJobTitleProperty));
		var dept = convertCFString(ABRecordCopyValue(person, kABDepartmentProperty));
		if (org || title || dept) {
			aContact.organizations = [{
					name: org,
					title: title,
					department: dept
				}]
		}
		var urls = ABRecordCopyValue(person, kABURLsProperty);
		for (var j=0;j<ABMultiValueCount(urls);j++)
		{
			if (!aContact.urls) aContact.urls = [];
			nativeType = convertCFString(ABMultiValueCopyLabelAtIndex(urls, j));			
			aContact.urls.push( {
				value:convertCFString(ABMultiValueCopyValueAtIndex(urls, j)),
				type: deriveLabelFromString(nativeType)
			}); 
		}
		var phones = ABRecordCopyValue(person, kABPhoneProperty);
		for (var j=0;j<ABMultiValueCount(phones);j++)
		{
			if (!aContact.phones) aContact.phones = [];
			nativeType = convertCFString(ABMultiValueCopyLabelAtIndex(phones, j));			
			aContact.phones.push( {
				value:convertCFString(ABMultiValueCopyValueAtIndex(phones, j)),
				type: deriveLabelFromString(nativeType)
			}); 
		}
		var addresses = ABRecordCopyValue(person, kABAddressProperty);
		for (var j=0;j<ABMultiValueCount(addresses);j++)
		{
			if (!aContact.addresses) aContact.addresses = [];
			nativeType = convertCFString(ABMultiValueCopyLabelAtIndex(addresses, j));
			anAddress = ABMultiValueCopyValueAtIndex(addresses, j);
			aContact.addresses.push( {
				streetAddress:     convertCFString(CFDictionaryGetValue(anAddress, kABAddressStreetKey)),
				locality:          convertCFString(CFDictionaryGetValue(anAddress, kABAddressCityKey)),
				region:            convertCFString(CFDictionaryGetValue(anAddress, kABAddressStateKey)),
				postalCode:        convertCFString(CFDictionaryGetValue(anAddress, kABAddressZIPKey)),
				country:           convertCFString(CFDictionaryGetValue(anAddress, kABAddressCountryKey)),
				countryCode:       convertCFString(CFDictionaryGetValue(anAddress, kABAddressCountryCodeKey)),
				type:              deriveLabelFromString(nativeType)
			}); 
		}
		var birthDate = ABRecordCopyValue(person, kABBirthdayProperty);
		if (birthDate) {
			aContact.birthday = convertCFDate(birthDate);
		}
		// picture data?  it's all TIFF so this may be a waste of time.
		/*
		var imageData = ABPersonCopyImageData(person);
		if (imageData && !imageData.isNull())
		{
			var imageDataLen = CFDataGetLength(imageData);
			var buf = new ctypes.ArrayType(ctypes.uint8_t, imageDataLen + 1)();
			var rg = new CFRange();
			rg.location = 0;
			rg.length = imageDataLen;
						
			//var b64 = base64EncodeCFData(imageData);
			//CFDataGetBytes(imageData, rg, ctypes.cast(buf, ctypes.voidptr_t));
			//aContact.rawPhotoData = buf;
			//console.log(firstName + " " + lastName + ": ");
			//console.log(b64);
			//console.log("Got " + imageDataLen + " image data bytes for " + firstName + " " + lastName + ": " + imageData);
		}*/
	
		// Construct a displayName:
		if (firstName && lastName) {
			aContact.displayName = firstName + " " + lastName;
		} else if (firstName) {
			aContact.displayName = firstName;
		} else if (lastName) {
			aContact.displayName = lastName;
		} else if (aContact.emails) {
			aContact.displayName = aContact.emails[0].value;
		}
		aContact.source = "native";
		aContact.id = i;
		contacts.push(aContact);
	}
	return contacts;
}



/** CFStringGetCharacters would be faster, but it isn't working for some reason */
function convertCFString(aString) {
	if (aString && !aString.isNull()) {
		var strLen = CFStringGetLength(aString);
		var targetBuffer = ctypes.jschar.array(strLen)();
		for (var i=0;i<strLen;i++) {
			targetBuffer[i] = CFStringGetCharacterAtIndex(aString, i);
		}
		var ret = targetBuffer.readString();
		if (ret && ret.length > 0) return ret;
		return null;
	} else {
		return null;
	}
}

function makeCFStr(input)
{
	return CFStringCreateWithCharacters(null, input, input.length);	
}

function convertCFDate(input)
{
	var t = CFDateGetAbsoluteTime(input);
	return new Date(t*1000 + 978307200000);
}

function getActivity(personAddrList)
{
	// Use MDFind services to find interesting mail...
	var query ="";
	for (var i in personAddrList) {
		if (i>0) query += " || ";
		query += "kMDItemAuthorEmailAddresses==\"" + personAddrList[i] + "\"wc";
	}
	queryStr = makeCFStr(query);
	
	var termArray = CFArrayCreateMutable(null, 2, null);
	CFArraySetValueAtIndex(termArray, 0, kMDItemDisplayName);
	CFArraySetValueAtIndex(termArray, 1, kMDItemContentCreationDate);
	
	var sortArray = CFArrayCreateMutable(null, 1, null);
	CFArraySetValueAtIndex(sortArray, 0, kMDItemContentCreationDate);
	
	var mdQuery = MDQueryCreate(null, queryStr, termArray, sortArray);
	var res = MDQueryExecute(mdQuery, 1);
	var count = MDQueryGetResultCount(mdQuery);
	console.log("MDQueryGetResultCount is " + count);

	var results = [];
	for (var i=0;i<count;i++) {
		var aName = MDQueryGetAttributeValueOfResultAtIndex(mdQuery, kMDItemDisplayName, i);
		var aDate = MDQueryGetAttributeValueOfResultAtIndex(mdQuery, kMDItemContentCreationDate, i);
		//var path = MDQueryGetAttributeValueOfResultAtIndex(mdQuery, kMDItemPath, i);		

		results.push({
			title:convertCFString(aName),
			date:convertCFDate(aDate)
		});
	}
	return results;
}

//// XXX WTB a function to convert any CFData into JS...

function getRecentActivity(callback)
{
	//var query = "kMDItemKind == \"Mail Message\" && kMDItemContentCreationDate == $time.this_week(-1)";
	// var query = "kMDItemFSContentChangeDate == $time.today";
	var query = "kMDItemContentTypeTree == 'public.email-message' && " +
		"kMDItemContentCreationDate >= $time.this_week(-1)";
	queryStr = makeCFStr(query);
	
	console.log("Executing query " + query);

	var termArray = CFArrayCreateMutable(null, 3, null);
	CFArraySetValueAtIndex(termArray, 0, kMDItemDisplayName);
	CFArraySetValueAtIndex(termArray, 1, kMDItemContentCreationDate);
	CFArraySetValueAtIndex(termArray, 2, kMDItemAuthorEmailAddresses);
	
	var sortArray = CFArrayCreateMutable(null, 1, null);
	CFArraySetValueAtIndex(sortArray, 0, kMDItemContentCreationDate);
	
	// XXX make async
	console.log("Making query");
	var mdQuery = MDQueryCreate(null, queryStr, termArray, sortArray);
	if (mdQuery.isNull()) {
		console.log("Query is null");
		return;
	}
	console.log("Executing query");
	var res = MDQueryExecute(mdQuery, 1);
	console.log("Getting result count (res is " + res + ")");
	var count = MDQueryGetResultCount(mdQuery);
	console.log("Got " + count + " results");

	var results = [];
	for (var i=0;i<count;i++) {
		var aName = MDQueryGetAttributeValueOfResultAtIndex(mdQuery, kMDItemDisplayName, i);
		var aDate = MDQueryGetAttributeValueOfResultAtIndex(mdQuery, kMDItemContentCreationDate, i);
		var anAuthorArray = MDQueryGetAttributeValueOfResultAtIndex(mdQuery, kMDItemAuthorEmailAddresses, i);
		var anAuthor = null;
		if (anAuthorArray && !anAuthorArray.isNull()) {
			var ct = CFArrayGetCount(anAuthorArray);
			if (ct) {
				anAuthor = CFArrayGetValueAtIndex(anAuthorArray, 0);
			} 
		}
		//var path = MDQueryGetAttributeValueOfResultAtIndex(mdQuery, kMDItemPath, i);		

		results.push({
			title:convertCFString(aName),
			date:convertCFDate(aDate),
			author:convertCFString(anAuthor)
		});

	}
	callback(results);
}
//console.log(JSON.stringify(getAllContacts()));
// console.log(getActivity("benadida@mozilla.com"));







/*
 * Base 64 implementation in JavaScript
 * Copyright (c) 2009 Nicholas C. Zakas. All rights reserved.
 * 
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */ 
 
/**
 * Base64-encodes a string of text.
 * @param {String} text The text to encode.
 * @return {String} The base64-encoded string.
 */
function base64EncodeCFData(data){
        
/*    if (/([^\u0000-\u00ff])/.test(text)){
        throw new Error("Can't base64 encode non-ASCII characters.");
    }   
 */
    var digits = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
        i = 0,
        cur, prev, byteNum,
        result=[];      

    ///  Hrrrm.   I can't get anything but zeroes out of this
    // function no matter how hard I try.
	var dataLen = CFDataGetLength(data);
	var tempStruct = ctypes.StructType("tempStruct" + dataLen, 
		[ {'data': ctypes.ArrayType(ctypes.uint8_t, dataLen) } ])
	var tempCFDataGetBytePtr = cflib.declare(
				"CFDataGetBytePtr",
				ctypes.default_abi,
				tempStruct,
				ctypes.voidptr_t); // takes CFDataRef
	var dataPointerStruct = tempCFDataGetBytePtr(data);
	var dataPointer = dataPointerStruct.data;
    
    console.log(dataPointerStruct);
    console.log(dataPointer);

    while(i < dataLen){
        
        cur = dataPointer.addressOfElement(i).contents;// [i];//.charCodeAt(i);
        if (i < 10) console.log("" + i + ": " + dataPointer.addressOfElement(i) + " " + cur);

        byteNum = i % 3;
        
        switch(byteNum){
            case 0: //first byte
                result.push(digits.charAt(cur >> 2));
                break;
                
            case 1: //second byte
                result.push(digits.charAt((prev & 3) << 4 | (cur >> 4)));
                break;
                
            case 2: //third byte
                result.push(digits.charAt((prev & 0x0f) << 2 | (cur >> 6)));
                result.push(digits.charAt(cur & 0x3f));
                break;
        }
        
        prev = cur;
        i++;
    }
    
    if (byteNum == 0){
        result.push(digits.charAt((prev & 3) << 4));
        result.push("==");
    } else if (byteNum == 1){
        result.push(digits.charAt((prev & 0x0f) << 2));
        result.push("=");
    }
 
    return result.join("");
}
