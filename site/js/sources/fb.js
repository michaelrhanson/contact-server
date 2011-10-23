function FacebookSource()
{
	return this;
}
FacebookSource.prototype =
{
	refresh: function(contactServer)
	{
		var self = this;
		console.log("Refreshing Facebook");
		var xhr = new XMLHttpRequest();
		xhr.open("GET", "/fb/me/friends", true);
		xhr.onreadystatechange = function(aEvt)
		{
			if (xhr.readyState == 4) {
				if (xhr.status == 200) {
					console.log("Got Facebook response");
					try {
						var result = JSON.parse(xhr.responseText);
					} catch (e) {
						return;
					}
					if (result.data) {
						for (var i in result.data) {
							var p = result.data[i];
							if (p.name) {
								p.displayName = p.name;
								p.name = {};
								var sp = p.displayName.split(" ");
								p.name.familyName = sp[sp.length-1];
								p.name.givenName = sp.splice(0, sp.length-1).join(" ");								
							}
							p.source = "facebook";
							p.urls = [
								{	
									type:"Facebook",
									value:"http://www.facebook.com/" + p.id
								}];
							p.photos = [
								{
									value: "https://graph.facebook.com/" + p.id + "/picture?type=small",
									type: "thumbnail"
								},
								{
									value: "https://graph.facebook.com/" + p.id + "/picture?type=normal",
									type: "w100",
									primary: true
								},
								{
									value: "https://graph.facebook.com/" + p.id + "/picture?type=large",
									type: "w200"
								}							
							]
							p.accounts = [
								{
									domain: "facebook.com",
									userid: p.id
								}
							]
						}
						contactServer.addContacts(result.data);
					}
				}
				contactServer.refreshFinished(self);
			}
		}
		xhr.send(null);
	},

	getActivity: function(contact, contactServer)
	{
		for (var i in contact.sources) {
			if (contact.sources[i].indexOf("facebook.") == 0) {
				var id = contact.sources[i].substring(9);
			}
		}
		if (id) {
			var xhr = new XMLHttpRequest();
			xhr.open("GET", "/fb/" + id + "/feed?limit=50", true);
			xhr.onreadystatechange = function(aEvt)
			{
				if (xhr.readyState == 4) {
					if (xhr.status == 200) {
						result = JSON.parse(xhr.responseText);
						if (result.data) {
							var out = [];
							for (var i = result.data.length-1; i>=0;i--) // reverse order
							{
								if (result.data[i].from && result.data[i].from.id == id)
								{
									var r = result.data[i];
									out.push(r);
									if (r.message) r.title = r.message;
									else if (r.name) {
										r.title = r.name;
									} else if (r.caption) {
										r.title = r.caption;
									}
									
									if (r.updated_time) r.date = new Date(r.updated_time.replace("+0000", "Z"));
									else if (r.created_time) r.date = new Date(r.created_time.replace("+0000", "Z"));
								}
							}
							contactServer.addActivity(contact, out);
    					}
					}
				}
			}
			xhr.send(null);
		}
	},

	discover: function(contact, callback) {
		var self = this;
		function handleDiscovery(id) {
			var xhr = new XMLHttpRequest();
			xhr.open("GET", "/fb/" + id + "/photos", true);
			xhr.onreadystatechange = function(aEvt)
			{
				if (xhr.readyState == 4) {
					if (xhr.status == 200) {
						result = JSON.parse(xhr.responseText);
						if (result) {
							var newRec = {};
							newRec.source = "fbgraph";
							newRec.id = id;
							newRec.photos_of = [];
							for (var i in result.data)
							{
								var d = result.data[i];
								var bestImage;
								for (var j in d.images) {
									if (d.images[j].width > 100 && d.images[j].width < 200) bestImage = d.images[j];
								}
								if (!bestImage) bestImage = d.picture;
								newRec.photos_of.push({
									link: d.link,
									src: bestImage.source
								})
							}
							newRec.accounts = [{domain:"facebook.com", userid:id}]; 
							callback(newRec);
						}
					}
				}
			}
			xhr.send(null);
		}

		if (contact.accounts) {
			for (var i in contact.accounts) {
				if (contact.accounts[i].domain == "facebook.com") {
					handleDiscovery(contact.accounts[i].userid);
				}
			}
		}

/*		if (contact.urls) {
			for (var i in contact.urls) {
				if (contact.urls[i].type == "Facebook") {
					handleDiscovery(contact.urls[i])
				}
			}
		}*/
	}
}

