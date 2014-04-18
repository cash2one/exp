#!/usr/bin/python

import sys
sys.path.append('/home/ec2-user/src/common')

from ashttpcommon import SessionRequestHandler
from aspasswdgen import ReadableRandomPassGen

from urlparse import urlparse
import Cookie
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urllib
import xmlrpclib
import optparse
from translate import *
import json

class TransHandler(SessionRequestHandler):
	""" 
			Common params:
			  c=[channel]
			  TODO. authenticate for channel. channel should be read from cookie.

			/tranc?q=[query]&s=[sentence]&url=[]
	      chrome api, return a json object of {query: translate}
	    /trana
			  android api, return json
			/tranhome?debug=s1?q=[query]&s=[sentence]&url=[]
			  home page for web visiting
	"""
	def handleValidRequestBegin(self, path, params, post_params):
		return 'c' in params
	def handle_tranc(self, path, params, post_params):
		out = 'invalid input'
		print 'params, ', params, 'post_params', post_params
		if ('q' in params) and ('s' in params) and ('url' in params) and ('c' in params):
			# from user selection
			query = params['q'].strip()
			channel = params['c'].strip()
			sentence = params['s'].strip()
			url = params['url'].strip()
			# TODO. infact, this instance should be kept in a dict, say {channel:youdao}.
			# also, dict should also be passed in, to avoid duplicate mem copy.
			# TODO. in this case, multi write on dict is also considerable, maybe set up a unique
			# dict server? In this case, only user data should be kept in BaseProcessor.
			youdao = YoudaoProcessor(channel)
			trans = youdao.Query(query, sentence, url)
			out = json.dumps({query: trans})
		elif ('q' in post_params) and ('c' in post_params):
			# read from post
			query = post_params['q'].strip()
			channel = post_params['c'].strip()
			sentence = post_params['s'].strip()
			youdao = YoudaoProcessor(channel)
			trans = youdao.Query(query, sentence)
			out = '<html><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><body>'
			out += trans
			out += '</body></html>'

		self.sendResponse(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(out)

	def handle_trana(self, path, params, post_params):
		channel = params['c'].strip();
		youdao = YoudaoProcessor(channel)

		buf = []
		for item in youdao.DumpAllQuery():
			query = item[0]
			translation = item[1]
			snippets = []
			for snippet, url_time in item[2].iteritems():
				snippets.append(snippet)
			buf.append([query, translation, snippets])
		out = json.dumps(buf)

		self.sendResponse(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(out)

	def handle_tranhome(self, path, params, post_params):
		channel = params['c'].strip();
		youdao = YoudaoProcessor(channel)
		message = None
		if 'q' in post_params:
			query = post_params['q'].strip()
			sentence = ''
			if 's' in post_params:
				sentence = post_params['s']
			url = None
			if 'url' in post_params:
				url = post_params['url']
			print query, sentence, url
			trans = youdao.Query(query, sentence, url)
			message = trans
		# Handle debug
		debug_info = None
		if 'debug' in params:
			debug_info = self.__debug_info(youdao)
		self.render(message, debug_info, title='dictionary')

	def __debug_info(self, youdao):
		out = ['<table border="1">']
		for item in youdao.DumpAllQuery():
			query = item[0]
			translation = item[1]
			snippets = item[2]
			out.append('<tr>')
			out.append('<td>%s</td>'%query)
			out.append('<td>%s</td>'%translation)
			out.append('<td><table>')
			for snippet, url_time in snippets.iteritems():
				out.append('<tr>')
				out.append('<td>%s</td>'%snippet)
				for url, ts in url_time.iteritems():
					if url != None and len(url) > 0:
						out.append('<td><a href="%s" target="_blank">%s</a></td>'%(url, url))
					else:
						out.append('<td></td>')
					out.append('<td>%s</td>'%self.__strftime(ts))
				out.append('</tr>')
			out.append('</table></td>')
			out.append('</tr>')
		out.append('</table>')
		return '\n'.join(out)

	def __strftime(self, ts):
		return ts.strftime('%Y-%m-%d %H:%M:%S')

	def render(self, message = None, debug_info = None, css_class = 'alert',
			status=200, title='chrome'):
		self.sendResponse(status)
		self.pageHeader(title)
		self.pageBody(message, debug_info, css_class)
		self.wfile.write('</body></html>')

	def pageBody(self, message, debug_info, css_class):
		if message:
			self.wfile.write("<div class='%s'>" % (css_class,))
			self.wfile.write(message)
			self.wfile.write("</div>")
		if debug_info:
			self.wfile.write("<div class='%s'>" % (css_class,))
			self.wfile.write(debug_info)
			self.wfile.write("</div>")

	def pageHeader(self, title):
		"""Render the page header"""
		self.wfile.write('''\
Content-type: text/html; charset=UTF-8

<html>
	<head><title>%s</title>
	<script type="text/javascript">
		function id(x) {
			if (typeof x == "string") return document.getElementById(x);
			return x;
		}
		function updateSiteName(site) {
			id("set-site-name").value = site;
		}
	</script>
	<style type="text/css">
			* {
				font-family: verdana,sans-serif;
			}
			body {
				width: 50em;
				margin: 1em;
			}
			div {
				padding: .5em;
			}
			tr.odd td {
				background-color: #dddddd;
			}
			table.sreg {
				border: 1px solid black;
				border-collapse: collapse;
			}
			table.sreg th {
				border-bottom: 1px solid black;
			}
			table.sreg td, table.sreg th {
				padding: 0.5em;
				text-align: left;
			}
			table {
				margin: 0;
				padding: 0;
			}
			.alert {
				border: 1px solid #e7dc2b;
				background: #fff888;
			}
			.error {
				border: 1px solid #ff0000;
				background: #ffaaaa;
			}
			.passfragment {
				padding: 0 0.15em;
				font-size: 1.5em;
				text-align: center;
				font-family: arial, sans-serif;
			}		#passphrase-form {
				border: 1px solid #777777;
				background: #dddddd;
				margin-top: 1em;
				padding-bottom: 0em;
			}
	</style>
	</head>
	<body>
    <div>
		  <form action="/tranhome" method="post">
				Query: <input type="text" name="q" />
				Sentence: <input type="text" name="s" />
				URL: <input type="text" name="url" />
				<input type="submit" value="Submit" />
			</form>
		</div>
''' % title)

if __name__ == '__main__':
	parser = optparse.OptionParser('Usage:\n %prog [options]')
	parser.add_option(
			'-p', '--port', dest='port', type='int', default=8017,
			help='Port on which to listen for HTTP requests. '
			'Defaults to port %default.')
	parser.add_option(
			'-s', '--host', dest='host', default='localhost',
			help='Host on which to listen for HTTP requests. '
			'Also used for generating URLs. Defaults to %default.')

	options, args = parser.parse_args()
	server = HTTPServer(('', options.port), TransHandler)
	print "http backend server serving at port", options.port
	server.serve_forever()

