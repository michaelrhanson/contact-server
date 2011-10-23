function GoogleContactsSource()
{
	return this;
}
GoogleContactsSource.prototype =
{
	refresh: function(contactServer)
	{
		var self = this;
		console.log("Refreshing Google Contacts");
		var xhr = new XMLHttpRequest();
		xhr.open("GET", "/google/contacts", true);
		xhr.onreadystatechange = function(aEvt)
		{
			if (xhr.readyState == 4) {
				if (xhr.status == 200) {
					console.log("Got Google response");
					result = JSON.parse(xhr.responseText);
					if (result.status == "ok") {
						for (var i in result.contacts) {
							var p = result.contacts[i];
							p.source = "google";
							if (!p.name) {
								p.name = {}
								if (p.displayName) {
									var sp = p.displayName.split(" ");
									p.name.familyName = sp[sp.length-1];
									p.name.givenName = sp.splice(0, sp.length-1).join(" ");									
								}
							}
							if (!p.displayName) {
								if (p.emails) {
									p.displayName = p.emails[0].value;
								}
							}
						}
						contactServer.addContacts(result.contacts);
					}
				}
				contactServer.refreshFinished(self);
			}
		}
		xhr.send(null);
	}
}

