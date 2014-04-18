# Note: it's not thread safe, use one cache per thread
# benefit: support cache, timeout
import httplib2
h = httplib2.Http('.cache', timeout = 10)
h.add_credentials('name', 'password')
(resp, content) = h.request("http://example.org/", "GET",
		headers={'content-type':'text/plain'} )
print resp
print content
