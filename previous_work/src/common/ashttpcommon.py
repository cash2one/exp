__copyright__ = 'Copyright 2011-2014, Yuliang Wang(yuliang.leon@gmail.com).'

from ascommon import FileStore, MemStore, StoreException, rand_string, shortReadableName
from asaes import AsAES

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import urlparse, urljoin
import urllib
from datetime import datetime, timedelta
from Cookie import SimpleCookie
import time
import random
import unittest
import cgitb
import sys

def GetCacheExpires(days_from_now):
	expires = datetime.now() + timedelta(days = days_from_now)
	return expires.strftime('%a, %d %b %Y %H:%M:%S')

def AddToParams(query, params):
	for param in query.strip().split('&'):
		items = param.split('=')
		if len(items) == 2:
			params[urllib.unquote_plus(items[0])] = urllib.unquote_plus(items[1])
		else:
			print items

# Token

import base64

class InvalidToken(Exception):
	def __init__(self, value='invalid token'):
		self.value = value
	def __str__(self):
		return self.value

def CreateToken(userid, passwd, root_passwd, timeout = 60*60*24):
	""" Some applicate donot need passwd, we set it to a default one.
	"""
	output = []
	output.append(userid)
	output.append(passwd)
	expiration = time.time() + timeout
	output.append(str(expiration))
	output.append('123456789')
	output.append(rand_string(16))

	message = '\n'.join(output)
	if message.split('\n') != output:
		raise InvalidToken('input include \\n')

	ciphered = AsAES(root_passwd).encrypt(message)
	token = base64.urlsafe_b64encode(ciphered)
	return token

def ParseToken(token, root_passwd):
	""" Parse token, if valid, return the userid and passwd
	"""
	decoded = base64.urlsafe_b64decode(token)
	try:
		message = AsAES(root_passwd).decrypt(decoded)
	except Exception:
		raise InvalidToken('Can not decrypt token')

	lines = message.split('\n')
	if len(lines) != 5:
		raise InvalidToken('lines is %d'%len(lines))
	userid = lines[0]
	passwd = lines[1]
	expiration = lines[2]
	salt = lines[3]
	# salt match
	if salt != '123456789':
		raise InvalidToken('salt invalid')
	# not expired
	if time.time() >= float(expiration):
		raise InvalidToken('token expired')
	return (userid, passwd)

class CheckToken(unittest.TestCase):
	def testTokenParse(self):
		token = CreateToken('test', 'test-passwd', 'root-passwd', 60 * 30)
		# total invalid token
		self.assertRaises(InvalidToken, ParseToken, 'af89\n\t0128$%!',
				'root-passwd')
		# wrong rootpasswd can not parse
		self.assertRaises(InvalidToken, ParseToken, token, 'root-passwd-2')
		# valid parse
		self.assertEquals(('test', 'test-passwd'), ParseToken(token, 'root-passwd'))
	def testTokenExpire(self):
		token = CreateToken('test', 'test-passwd', 'root-passwd', 0)
		time.sleep(0.1)
		self.assertRaises(InvalidToken, ParseToken, token, 'root-passwd')

def userPassValidInFile(userid, userpass, store = FileStore(),
		dir = '/home/ec2-user/src/superpass/data'):
	""" check user input (userid, userpass) match we stored in file
	if file not exist, create one."""
	storekey = '%s/%s.key'%(dir, shortReadableName(userid))
	user_encoded = AsAES(userpass).encrypt(userid)
	try:
		saved_text = store.read(storekey)
	except StoreException:
		store.write(storekey, user_encoded)
		return True
	else:
		return user_encoded == saved_text

class CheckUserPassValid(unittest.TestCase):
	def testReadWrite(self):
		store = MemStore()
		# create 3 entry
		self.assertTrue(userPassValidInFile('test', 'test-pass', store))
		self.assertTrue(userPassValidInFile('test2', 'test-pass2', store))
		self.assertTrue(userPassValidInFile('test3', 'test-pass', store))
		# same user, different passwd
		self.assertFalse(userPassValidInFile('test', 'test-pass2', store))
		self.assertFalse(userPassValidInFile('test2', 'test-pass', store))
		self.assertFalse(userPassValidInFile('test3', 'test-pass2', store))
		# same user, same passwd
		self.assertTrue(userPassValidInFile('test', 'test-pass', store))
		self.assertTrue(userPassValidInFile('test2', 'test-pass2', store))
		self.assertTrue(userPassValidInFile('test3', 'test-pass', store))
		# different user, same or different passwd
		self.assertTrue(userPassValidInFile('test4', 'test-pass', store))
		self.assertTrue(userPassValidInFile('test5', 'test-pass5', store))



# HTTP handlers
# TODO. instead of inherit, consider composite.
class DispatchHTTPRequestHandler(BaseHTTPRequestHandler):
	""" dispatch according to root path.
			call handle_login('/login', {user:test}) for '/login?user=test'
			call handle_verify('/verify/other/path', {user:x}) for '/verify/other/path?user=x'
			call handle_('/', {}) for '/'
			call handle_('', {}) for ''

			call handleErrorMatch for any unmatched path
			call handleException for unknow exception
	"""

	def do_GET(self):
		self.__cached_cookie = {}
		self.__handleRequest()

	def do_POST(self):
		self.__cached_cookie = {}
		clen = self.headers.getheader('content-length')
		if clen:
			clen = int(clen)
		else:
			print 'Invalid content length'
			return
		print 'Got post request for %d length'%clen
		params = {}
		if clen > 0:
			AddToParams(self.rfile.read(clen), params)
		self.__handleRequest(params)

	def __handleRequest(self, post_params = {}):
		path = ''
		params = {}
		try:
			parsed_url = urlparse(self.path)
			AddToParams(parsed_url.query, params)
			path = parsed_url.path
	
			items = path.strip('/').split('/')
			root_path = ''
			if len(items) > 0:
				root_path = items[0]
	
			func = getattr(self, 'handle_%s'%root_path, self.handleErrorMatch)
			if func != self.handleErrorMatch:
				if not self.handleValidRequestBegin(path, params, post_params):
					return
			func(path, params, post_params)
		except (KeyboardInterrupt, SystemExit):
			raise
		except Exception as e:
			print 'Exception happend ', e
			self.handleException(path, params, post_params)

	def handleValidRequestBegin(self, path, params, post_params):
		return True

	def handleErrorMatch(self, path, params, post_params):
		self.sendResponse(404)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		msg = 'unknow path %s'%path
		self.wfile.write(msg)
	
	def handleException(self, path, params, post_params):
		self.sendResponse(500)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		msg = cgitb.html(sys.exc_info(), context=10)
		print msg
		# TODO. Not display the error message.
		self.wfile.write(msg)

	def redirect(self, redirect_url):
		print 'Redirect to', redirect_url
		self.sendResponse(302)
		self.send_header('Location', redirect_url)
		#self.writeUserHeader()
		self.end_headers()

	def redirectWithTimeout(self, redirect_url, message, timeout = 1):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write(
				"""<html><head><meta HTTP-EQUIV="REFRESH" content="%i; url=%s"/>
				</head><body>%s</body></html>"""%(timeout, redirect_url, message))
	
	def readCookie(self, name):
		cookie_str = self.headers.get('Cookie')
		print 'cookie:', cookie_str
		if cookie_str:
			c = SimpleCookie(cookie_str)
			cookie_morsel = c.get(name, None)
			if cookie_morsel is not None:
				return cookie_morsel.value
		return None

	def writeCookie(self, name, value, path = '/', days_from_now = 30):
		""" cache the cookie set until response sent.
		"""
		c = SimpleCookie()
		c[name] = value
		c[name]['path'] = path
		c[name]['expires'] = GetCacheExpires(days_from_now)
		self.__cached_cookie[name] = c.output(header='')

	def clearCookie(self, name):
		""" cache the cookie set until response sent.
		"""
		c = SimpleCookie()
		c[name] = ''
		c[name]['path'] = '/'
		c[name]['expires'] = 0
		self.__cached_cookie[name] = c.output(header='')

	def sendResponse(self, response_code):
		""" To ensure Set-Cookie header is called after sendResponse,
		call sendResponse instead of sendResponse.
		"""
		# TODO. do we need to overwrite send_response?
		self.send_response(response_code)
		print 'send response %d'%response_code
		for v in self.__cached_cookie.itervalues():
			self.send_header('Set-Cookie', v)
			print 'set cookie %s'%v

class SessionRequestHandler(DispatchHTTPRequestHandler):
	""" Force a session exist when handling http request.
	"""

	def getSession(self, name):
		""" Get name in session, return None is not exist
		"""
		session = self.getRawSession()
		if name in session:
			return session[name]
		else:
			return None

	def setSession(self, name, value):
		session = self.getRawSession()
		session[name] = value

	def getRawSession(self):
		try:
			session = self.session
		except Exception:
			# Get sid from cookie.
			sid = self.readCookie('sid')
			if sid is None:
				sid = rand_string(16)
				self.writeCookie('sid', sid)
			# TODO. create a SessionServer and try read session back from server.
			session = {}
			session['id'] = sid
			self.session = session
		return session

if __name__ == '__main__':
	unittest.main()

