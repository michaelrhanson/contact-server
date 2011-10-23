function GravatarContactsSource()
{
	return this;
}
GravatarContactsSource.prototype =
{
	refresh: function(contactServer)
	{
	},
	
	discover: function(contact, callback)
	{
		var self = this;
		function handleAddress(emailObj) {
			var xhr = new XMLHttpRequest();
			var addr = emailObj.value;
			xhr.open("GET", "/gravatar/" + addr, true);
			xhr.onreadystatechange = function(aEvt)
			{
				if (xhr.readyState == 4) {
					if (xhr.status == 200) {
						result = JSON.parse(xhr.responseText);
						if (result) {
							result.source = "gravatar";
							result.id = addr;
							// gravatar displayNames are often used like handles.
							// some way to downrank it?
							// attach email so discovery works later
							result.emails = [{type:emailObj.type, value:addr}]; 
							callback(result);
						}
					}
				}
			}
			xhr.send(null);
		}

		if (contact.emails) {
			for (var i in contact.emails) {
				handleAddress(contact.emails[i]);
			}
		}
	}

}

