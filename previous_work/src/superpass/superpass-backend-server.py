#!/usr/bin/python

import sys
sys.path.append('/home/ec2-user/src/common')

from ashttpcommon import SessionRequestHandler, ParseToken
from superpass import PersonalPassStorage
from aspasswdgen import ReadableRandomPassGen

from urlparse import urlparse
import Cookie
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urllib
import xmlrpclib
import optparse

def getRootKey():
	return xmlrpclib.ServerProxy('http://localhost:8180').GetUniqueKey()

class MyServer(HTTPServer):
	""" Server will not store any user password.
			Server keep as less information as possible, so it's more scalable and
			more safe, and more efficient(no need to clean, threading, etc.).
			e.g: server will not keep a token map for users, or a user info map for
			users.
			Solution:
			* server start, get a root_key from chubby which is used for tokens.
			* support the following path:
				- /spls
				- /spget?site=[]
				- /spgethis?site=[]
				- /spset?site=[]&passwd=[] VIA POST
				all the path will check the token from cookie first,
				if not valid, redirect to	/login?needps=1&back=/spls.
				else show the message.

				Note. server can have a popular cache (username, token, pps) to improve
				speed.
	"""
	def __init__(self, server_address, handler):
		HTTPServer.__init__(self, server_address, handler)
		# Note. Read only, no need to mutex.
		self.pass_gen = ReadableRandomPassGen()
		self.root_key = getRootKey()

class MyHandler(SessionRequestHandler):
	""" Note. rm and changepass, do we need it?
		If don't provide rm and changepass, then even you leaked the super
		password, then your password just go public. Nobody can delete them, all
		you need to do is create another user and back up the data.
	"""
	def handleValidRequestBegin(self, path, params, post_params):
		# For any request, check token first.
		if not self.hasValidToken():
			self.redirect('/login?needps=1&back=spls')
			return False
		(userid, userpasswd) = ParseToken(self.readCookie('stoken'), self.server.root_key)
		try:
			self.setSession('pps', PersonalPassStorage(userid, userpasswd))
		except Exception as e:
			print 'cammot get data', e
			self.render(message = 'server error. cannot get data',
					css_class = 'error', status=500)
			return False
		return True

	def hasValidToken(self):
		""" If valid, set the self._pps
		"""
		token = self.readCookie('stoken')
		if token is None:
			return False
		try:
			(userid, userpasswd) = ParseToken(token, self.server.root_key)
		except Exception:
			# try update the root key and parse again
			# TODO. No need to getRootKey in 10 seconds.
			self.server.root_key = getRootKey()
			try:
				(userid, userpasswd) = ParseToken(token, self.server.root_key)
			except Exception:
				return False
		return True

	def handle_spls(self, path, params, post_params):
		self.render()
	def handle_spget(self, path, params, post_params):
		site = params['site']
		html = MyHandler.htmlForPasswds(site,
				[self.getSession('pps').get(site)])
		self.render(html)
	def handle_spgethis(self, path, params, post_params):
		site = params['site']
		html = MyHandler.htmlForPasswds(site,
				self.getSession('pps').getHis(site).split())
		self.render(html)
	def handle_spset(self, path, params, post_params):
		site = post_params['site']
		newpasswd = post_params['newpasswd']
		self.getSession('pps').append(site, newpasswd)
		self.render('succeed seting new password for %s'%site)

	def handle_spdump(self, path, params, post_params):
		pps = self.getSession('pps')
		txt = pps.outputPasswdTxt()
		html = txt.replace('\n', '<br/>')
		self.render(dump=html)

	@staticmethod
	def htmlForPasswds(site, passwds):
		output = ['site %s:<br/>'%site]
		for passwd in passwds:
			num = len(passwd) / 4 
			for i in range(num - 1):
				output.append('<span class="passfragment">%s</span>'%passwd[i*4 : (i+1)*4])
			output.append('<span class="passfragment">%s</span>'%passwd[(num-1)*4 : ])
			output.append('<br/>')
		return ''.join(output)
	
	def render(self, message = None, css_class = 'alert',
			status=200, title='superpass', dump=None):
		self.sendResponse(status)
		self.pageHeader(title)
		self.pageBody(message, css_class, dump)
		self.wfile.write('</body></html>')

	def pageBody(self, message, css_class, dump):
		if message:
			self.wfile.write("<div class='%s'>" % (css_class,))
			self.wfile.write(message)
			self.wfile.write("</div>")
		if self.getSession('pps') is None:
			return
		# the main body
		self.wfile.write('list results<br/>')
		for site in self.getSession('pps').list():
			self.wfile.write(
					"""%s	<a href="/spget/get?site=%s">get</a>
					<a href="/spgethis/gethis?site=%s">history</a>
					<a href="javascript:void(0);" onClick="updateSiteName('%s');">set</a>
					<br/>"""%(site, site, site, site))
		# the new form.
		newpasswd = self.server.pass_gen.Get()
		self.wfile.write(
				"""<form method="post" action="/spset">
				<span>site:</span>
				<input name="site" id="set-site-name" type="text">
				<span>newpasswd:</span>
				<input name="newpasswd" type="text" value="%s">
				<input type="submit" value="create">
				</form><br/>"""%(newpasswd))
		# the output and load section.
		self.wfile.write("""<a href="/spdump">dump</a><br/>""")
		if dump is not None:
			self.wfile.write("""Your passwords:<div>%s</div>"""%dump)
		# the logout link
		self.wfile.write("""<a href="/logout?needps=1&back=spls">logout</a>""")

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
''' % title)

if __name__ == '__main__':
	parser = optparse.OptionParser('Usage:\n %prog [options]')
	parser.add_option(
			'-p', '--port', dest='port', type='int', default=8001,
			help='Port on which to listen for HTTP requests. '
			'Defaults to port %default.')
	parser.add_option(
			'-s', '--host', dest='host', default='localhost',
			help='Host on which to listen for HTTP requests. '
			'Also used for generating URLs. Defaults to %default.')

	options, args = parser.parse_args()
	server = MyServer((options.host, options.port), MyHandler)
	print "http backend server serving at port", options.port
	server.serve_forever()

