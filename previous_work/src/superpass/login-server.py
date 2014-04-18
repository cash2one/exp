__copyright__ = 'Copyright 2011-2014, Yuliang Wang(yuliang.leon@gmail.com).'

import sys
sys.path.append('/home/ec2-user/src/common')

from ashttpcommon import SessionRequestHandler, CreateToken, ParseToken, userPassValidInFile

import cgitb
import urlparse
import sys
import optparse
import urllib
from BaseHTTPServer import HTTPServer
import xmlrpclib

try:
	import openid
except ImportError:
	sys.stderr.write(""" Failed to import the OpenID library. """)
	sys.exit(1)
from openid.consumer import consumer
from openid.extensions import pape, sreg

class LoginServer(HTTPServer):
	def __init__(self, *args, **kwargs):
		HTTPServer.__init__(self, *args, **kwargs)
		self.base_url = 'https://zian.so/'

class LoginRequestHandler(SessionRequestHandler):
	""" Typical flow:
	/login?needps=.&back=app from /app redirect if no token.
		if not valid token:
			show a sign in link, which point to /openidverify?needps=.&back=app
		else:
			if not needps:
				302 to /app. (app will check token again, and see if have strong ps as required)
			else:
				if has post no empty passphrase:
					302 to /app.
				else:
					show a passphrase input, which post to /login?needps=1&back=app

	/openidverify?needps=1&back=app from user click
			will do the verification with openid provider, and redirect user to openid
			provider

	/openidprocess?needps=1&back=app&... from openid provider
			will verify with openid provider for the user
			if success:
				set token in cookie
				302(may be internal?) to /login?needps=1&back=app
	"""
	def getConsumer(self):
		return consumer.Consumer(self.getRawSession(), None)

	def handleErrorMatch(self, path, params, post_params):
		msg = 'The path <q>%s</q> was not understood by this server.'%self.path
		self.render(msg, 'error', status=404)

	def handle_logout(self, path, params, post_params):
		self.clearCookie('token')
		self.clearCookie('stoken')
		self.redirect('/login?%s'%urllib.urlencode(params))

	def handle_login(self, path, params, post_params):
		""" TODO. token type.
		- partial token. not include pasphrase. generate if
		  1. needps = 0
			2. needps = 1, but finished openid request.
			partial token means user have authorized by 3rd party orgnization.
		- full token. include passphrase
		"""
		root_key = xmlrpclib.ServerProxy('http://localhost:8180').GetUniqueKey()

		# not valid token
		try:
			token = self.readCookie('token')
			(userid, passwd) = ParseToken(token, root_key)
		except Exception:
			print 'invalid token in cookie'
			self.render(message = 'Please login',
					verify_link = '/openidverify?%s'%urllib.urlencode(params))
			return

		# From now on, it's a valid user., never clear the token in cookie

		# no need passphrase
		need_ps = params.get('needps', None)
		if need_ps is None or need_ps != '1':
			self.backToApp(params)
			print 'back to app for no need passphrase'
			return

		# Get stoken from passphrase or cookie.
		passphrase = post_params.get('passphrase', None)
		if passphrase is not None:
			# User do input. verify if we can access the file.
			if userPassValidInFile(userid, passphrase):
				stoken = CreateToken(userid, passphrase, root_key)
				self.writeCookie('stoken', stoken)
				self.backToApp(params)
				print 'back to app for passphrase is right'
				return
		# either user not input or their input is wrong here.
		# if cookie stoken can use, we should also redirect.
		try:
			stoken = self.readCookie('stoken')
			(userid, passwd) = ParseToken(stoken, root_key)
			if userPassValidInFile(userid, passphrase):
				self.backToApp(params)
				print 'back to app for stoken is still valid'
				return
		except Exception:
			pass

		self.render(
				message = 'Please enter your passphrase(more than 6 chars)',
				loginps_url = '/login?%s'%urllib.urlencode(params),
				css_class = 'error')


	def handle_openidverify(self, path, params, post_params):
		# First, make sure that the user entered something
		openid_url = "https://www.google.com/accounts/o8/id"
		oidconsumer = self.getConsumer()

		error_string = ''
		try:
			request = oidconsumer.begin(openid_url)
		except consumer.DiscoveryFailure, exc:
			error_string = 'Error in discovery: %s' % (urllib.quote(str(exc[0])))
		else:
			if request is None:
				error_string = 'No OpenID services found for <code>%s</code>' % (
						urllib.quote(openid_url),)
			else:
				request.addExtension(
						sreg.SRegRequest(required=['nickname'], optional=['fullname', 'email']))
				request.addExtension(pape.Request([pape.AUTH_PHISHING_RESISTANT]))

				trust_root = self.server.base_url
				return_to = '%sopenidprocess?%s'%(self.server.base_url, urllib.urlencode(params))
				
				if request.shouldSendRedirect():
					redirect_url = request.redirectURL(trust_root, return_to, immediate=False)
					self.redirect(redirect_url)
					print 'redirect to', redirect_url
				else:
					form_html = request.htmlMarkup(
							trust_root, return_to,
							form_tag_attrs={'id':'openid_message'},
							immediate=False)
					self.wfile.write(form_html)
					print 'form html', form_html
				return
		self.render(error_string, css_class='error')

	def handle_openidprocess(self, path, params, post_params):
		oidconsumer = self.getConsumer()
		complete_url = urlparse.urljoin(self.server.base_url, self.path)
		info = oidconsumer.complete(params, complete_url)
		display_identifier = info.getDisplayIdentifier()
		if display_identifier:
			userid = urllib.quote(display_identifier)

		css_class = 'error'

		if info.status == consumer.FAILURE and display_identifier:
			message = "Verification of %s failed: %s" % (userid, info.message)
		elif info.status == consumer.SUCCESS:
			if info.endpoint.canonicalID:
				message = "i-name not supported"
			else:
				css_class = 'alert'
				message = "You have successfully verified %s as your identity." % userid
				# set a init token, this is a good user from now on.
				self.writeToken(userid, 'anyRandomNotUsed')
				newparams = {}
				if 'back' in params:
					newparams['back'] = params['back']
				if 'needps' in params:
					newparams['needps'] = params['needps']
				self.redirect('/login?%s'%urllib.urlencode(newparams))
				return
		elif info.status == consumer.CANCEL:
			message = 'Verification cancelled'
		elif info.status == consumer.SETUP_NEEDED:
			if info.setup_url:
				message = '<a href=%s>Setup needed</a>' % (urllib.quote(info.setup_url),)
			else:
				message = 'Setup needed'
		else:
			message = 'Verification failed with status %s'%str(info.status)
		self.render(message, css_class)
	
	def writeToken(self, userid, passwd):
		root_key = xmlrpclib.ServerProxy('http://localhost:8180').GetUniqueKey()
		token = CreateToken(userid, passwd, root_key)
		self.writeCookie('token', token)

	def backToApp(self, params):
		if not 'back' in params:
			self.render('no where to back', 'error')
			return
		app = params['back']
		# Note. if app is invalid, please do not redirect to login page with back param
		if 'handle_%s'%app in dir(self):
			self.render('BUG. the app %s is conflict with one of the login handler'%app)
			return
		redirect_url = '/%s'%app
		self.redirect(redirect_url)
		return

	def render(self, message = None, css_class = 'alert',
						 verify_link = '', loginps_url = '',
						 status=200, title="Login"):
		self.sendResponse(status)
		self.pageHeader(title)
		if message:
			self.wfile.write("<div class='%s'>" % (css_class,))
			self.wfile.write(message)
			self.wfile.write("</div>")
		if verify_link != '':
			# TODO. show a image.
			self.wfile.write('<a href="%s">Login in Google</a>'%verify_link)
		if loginps_url != '':
			self.wfile.write("""\
			<div id = "passphrase">
				<form method="post" accept-charset="UTF-8" action=%s>
					<span>password</span><input name="passphrase" id = "passphrase" type="password">
					<input type="submit" value="OK">
				</form>
			</div>
"""%loginps_url)
		self.wfile.write('</body></html>')

	def pageHeader(self, title):
		"""Render the page header"""
		self.wfile.write('''\
Content-type: text/html; charset=UTF-8

<html>
	<head><title>%s</title></head>
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
			#passphrase-form {
				border: 1px solid #777777;
				background: #dddddd;
				margin-top: 1em;
				padding-bottom: 0em;
			}
	</style>
	<body>
''' % title)

def main(host, port):
	server = LoginServer((host, port), LoginRequestHandler)
	print 'Login server running at %s:%d'%(host, port)
	server.serve_forever()

if __name__ == '__main__':
	# command line flags handle
	parser = optparse.OptionParser('Usage:\n %prog [options]')
	parser.add_option(
			'-p', '--port', dest='port', type='int', default=8109,
			help='Port on which to listen for HTTP requests. '
			'Defaults to port %default.')
	parser.add_option(
			'-s', '--host', dest='host', default='localhost',
			help='Host on which to listen for HTTP requests. '
			'Also used for generating URLs. Defaults to %default.')
	
	options, args = parser.parse_args()
	if args:
		parser.error('Expected no arguments. Got %r' % args)

	main(options.host, options.port)
