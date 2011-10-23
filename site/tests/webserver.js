/*
 *  A nodejs testing server for running the various sites involved in
 *  vapour locally.  The following sites are served here:
 *
 *  myapps.org - Both the HTML5 site dashboard and the broker of application
 *               purchasing and provising
 *  apptast.ic - An application store, perhaps one that is capable of morphing
 *               plain ol' websites into applications
 *  spaceface.com - A web site that can be installed as a web application.
 *
 *  The server also does code parameterization for local testing.  The hostnames
 *  above will be substituted within served html, javascript, and css at the
 *  time they're served.  This allows local testing without any etc hosts
 *  modification.
 */

var sys = require("sys"),
http = require("http"),
url = require("url"),
path = require("path"),
fs = require("fs");

const sites = {
    "test": {
        dir: "./",
        prod_url: 'http://test.com',
        dev_port: "8123"
    },    
};

function createServer(port) {
    return http.createServer(function(request, response) {
        var hostname = request.headers['host'].toString("utf8");

        var siteroot = null;
        for (s in sites) {
            var port = hostname.split(":")[1];
            if (port == sites[s].dev_port) {
                console.log("req for host: " + s + " (port "+ sites[s].dev_port  + ")");
                siteroot = sites[s].dir;
                break;
            }
        }

        if (siteroot === null) {
            response.writeHead(404, {"Content-Type": "text/plain"});
            response.write("404 Not Found");
            response.end();
            console.log("404 " + hostname);
            return;
        }

        console.log("Siteroot: " + siteroot);

        var uri = url.parse(request.url).pathname;
        var filename = path.join(process.cwd(), siteroot, uri);

        console.log("filename: " + siteroot);


        // I'd like to use this to normalize HTML (optionally):
        //   http://github.com/aredridel/html5
        // Maybe turn it into XML/XHTML so it's easy to parse browser-side
        var parsedURI = url.parse(request.url, true);
        if (parsedURI.pathname == '/subreq') {
            var makeRequest = function (getURI) {
                getURI = url.parse(getURI);
                getURI.pathname = getURI.pathname || '/';
                getURI.search = getURI.search || '';
                getURI.port = getURI.port || '80';
                var client = http.createClient(parseInt(getURI.port), getURI.hostname);
                var siteRequest = client.request('GET',
                    getURI.pathname + getURI.search,
                    {host: getURI.host});
                siteRequest.end();
                siteRequest.on('response', function (siteResponse) {
                    if (parsedURI.query.follow
                        && siteResponse.statusCode > 300
                        && siteResponse.statusCode < 400) {
                        getURI = siteResponse.headers['location'];
                        sys.puts('Proxy redirect to: ' + getURI);
                        makeRequest(getURI);
                        return;
                    }
                    response.writeHead(
                        siteResponse.statusCode, siteResponse.headers);
                    siteResponse.on('data', function (chunk) {
                        response.write(chunk, 'binary');
                    });
                    siteResponse.on('end', function () {
                        response.end();
                    });
                });
            };
            makeRequest(parsedURI.query.uri);
            sys.puts("Proxy URL " + parsedURI.query.uri);
            return;
        }

        var serveFile = function (filename) {
        
            function serveFromPath(filename)
            {
             fs.readFile(filename, "binary", function(err, data) {
                  if(err) {
                      response.writeHead(500, {"Content-Type": "text/plain"});
                      response.write(err + "n");
                      response.end();
                      sys.puts("500 " + filename);
                      return;
                  }

                  // determine content type.  all text/ types will get hostnames replaced
                  var exts = {
                      ".js":   "text/javascript",
                      ".css":  "text/css",
                      ".html": "text/html",
                      ".htm": "text/html",
                      ".webapp": "application/x-web-app-manifest+json"
                  };
                  var ext = path.extname(filename);
                  var mimeType = (exts[ext]) ? exts[ext] : "application/unknown";

                  if ('text' === mimeType.substr(0,4) && data && data.split) {
                      // which hostname shall we substituted in?
                      var subHost = hostname.split(":")[0];
                      for (s in sites) {
                          // data = data.split(sites[s].prod_url).join("http://" + subHost + ":" + sites[s].dev_port);
                      }
                  }

                  response.writeHead(200, {"Content-Type": mimeType});
                  response.write(data, "binary");
                  response.end();
                  sys.puts("200 " + filename);
              });
            }
            function serve404()
            {
              response.writeHead(404, {"Content-Type": "text/plain"});
              response.write("404 Not Found");
              response.end();
              sys.puts("404 " + filename);
              return;
            }

            console.log("serving " + filename);
            path.exists(filename, function(exists) {
              if(!exists) {
                serve404();
              } else {
                serveFromPath(filename);
              }
            });
        };

        // automatically serve index.html if this is a directory
        fs.stat(filename, function(err, s) {
            if (err === null && s.isDirectory()) {
                serveFile(path.join(filename, "index.html"));
            } else {
                serveFile(filename);
            }
        });
    }).listen(port);
};
var ports = [];
for (s in sites) {
    if (sites[s].nobind) continue;
    var p = parseInt(sites[s].dev_port);
    sys.puts("bound http://localhost:" + p + " - " + sites[s].prod_url);
    createServer(p);
    ports.push(p);
}
