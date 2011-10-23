var gPendingContactServer;
var gPendingContact;
var gRecentActivityCallback; // XXX replace with a table of inflight request?

self.on('message', function onMessage(message)
{
	if (message.cmd == "refresh")
	{
		if (gPendingContactServer) {
			gPendingContactServer.addContacts(message.contacts);
			gPendingContactServer.refreshFinished();
		}
	} else if (message.cmd == "getactivity")
	{
		for (var i in message.activity) { // reinflate dates
			message.activity[i].date = new Date(message.activity[i].date);
			message.activity[i].icon = "/static/i/message.png";
		}
		gPendingContactServer.addActivity(gPendingContact, message.activity);
	} else if (message.cmd == "getrecentactivity")
	{
		gRecentActivityCallback(message.activity);
	}

});

function MacLocalContactSource()
{
	return this;
}
MacLocalContactSource.prototype =
{
	refresh: function(contactServer)
	{
		console.log("Refreshing Mac local contacts");
		gPendingContactServer = contactServer;
		self.postMessage({cmd:"refresh"});
	},

	getActivity: function(contact, contactServer)
	{
		// XXXX someday, handle changes in flight
		console.log("Getting Mac local activity for " + contact.displayName);
		gPendingContactServer = contactServer;
		gPendingContact = contact;
		self.postMessage({cmd:"getactivity", target:contact});
	},

	getRecentActivity: function(callback)
	{
		console.log("Getting Mac recent local activity");
		gRecentActivityCallback = callback;
		self.postMessage({cmd:"getrecentactivity"});		
	}

}

unsafeWindow.MacLocalContactSource = MacLocalContactSource;

console.log("Finished content script");