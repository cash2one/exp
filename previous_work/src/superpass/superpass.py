#!/usr/bin/python

__copyright__ = 'Copyright 2011-2014, Yuliang Wang(yuliang.leon@gmail.com).'

import sys
sys.path.append('/home/ec2-user/src/common')

import ascommon
from aspasswdgen import ReadableRandomPassGen
from asaes import AsAES

import getpass
import optparse
import unittest
import base64
import hashlib

class InvalidAccess(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class PersonalPassStorage:
	""" Storage:
	username
	sitenameA passA1 passA2 passA3
	sitenameB passB1
	"""
	def __init__(self, username, passwd = 'ABCDEFG1234567',
			store = ascommon.FileStore(), dir='/home/ec2-user/src/superpass/data', hislimit = 100):
		self.__username = username
		self.__aes = AsAES(passwd)
		self.__store = store
		self.__hislimit = hislimit
		self.__dict = {}
		self.__storekey = '%s/%s.pps'%(dir, ascommon.shortReadableName(username))
		# get from disk
		ciphertext = ''
		try:
			# TODO. save data to separate data dir.
			ciphertext = self.__store.read(self.__storekey)
		except ascommon.StoreException:
			# another user with empty data.
			self.dump_to_disk()
			return
		# decrypt
		message = self.__aes.decrypt(ciphertext)
		# Check the salt
		lines = message.split('\n')
		if len(lines) < 1 or lines[0] != '1234567890':
			raise InvalidAccess('invalid password for user %s '%self.__username)

		for line in lines[1:]:
			items = line.split()
			if len(items) < 2:
				continue
			self.__dict[items[0]] = ' '.join(items[1:])
		self.dump_to_disk()

	def get(self, sitename):
		return self.__dict[sitename].split()[-1]

	def getHis(self, sitename):
		return self.__dict[sitename]

	def list(self):
		allnames = [ k for (k, v) in self.__dict.iteritems() ]
		allnames.sort()
		return allnames

	def append(self, sitename, sitepass):
		if len(sitepass.split()) > 1:
			raise InvalidAccess('password include empty space?')
		if sitename in self.__dict:
			self.__dict[sitename] += ' %s'%sitepass
		else:
			self.__dict[sitename] = sitepass

		value = self.__dict[sitename]
		plist = value.split()
		if len(plist) > self.__hislimit:
			self.__dict[sitename] = ' '.join(plist[1:])

		self.dump_to_disk()

	def changeRoot(self, newpasswd):
		self.__aes = AsAES(newpasswd)
		self.dump_to_disk()

	def outputPasswdTxt(self):
		"""For user dumping their passwd"""
		return '\n'.join([ "%s %s"%(k, v) for (k, v) in self.__dict.iteritems() ])
	def loadPasswdTxt(self, txt):
		"""For user loading their passwd. transactional"""
		if txt == '':
			return
		# check format
		dic = {}
		for line in txt.split('\n'):
			if line == '':
				continue
			items = line.strip().split()
			if len(items) == 0:
				continue
			if len(items) < 2:
				raise InvalidAccess('items < 2 in line "%s"'%line)
			dic[items[0]] = items[1:]

		for k, v in dic.iteritems():
			for single_pass in v:
				self.append(k, single_pass)

	def dump_to_disk(self):
		# Encrypt
		message = '1234567890\n%s'%(self.outputPasswdTxt())
		ciphertext = self.__aes.encrypt(message)
		# Save to disk
		self.__store.write(self.__storekey, ciphertext)

import time
class CheckSuperpass(unittest.TestCase):
	@staticmethod
	def getStore(username = 'unittest',	passwd = 'unittestpasswd', limit = 100):
		return PersonalPassStorage(username, passwd, ascommon.MemStore(), hislimit=limit)
	def testOutputAndLoad(self):
		# Save and recover are equal
		pps = CheckSuperpass.getStore()
		for i in range(10):
			txt = pps.outputPasswdTxt()
			pps2 = CheckSuperpass.getStore('anotheruser', 'diffpasswd')
			pps2.loadPasswdTxt(txt)
			self.assertEquals(txt, pps2.outputPasswdTxt())
			pps.append(str(i), '%d-pass'%i)

		# Invalid load
		txt = pps.outputPasswdTxt()
		self.assertRaises(Exception, pps.loadPasswdTxt, ' a')
		self.assertRaises(Exception, pps.loadPasswdTxt, 'a')
		self.assertRaises(Exception, pps.loadPasswdTxt, 'a ')
		self.assertRaises(Exception, pps.loadPasswdTxt, 'ab   ')
		self.assertRaises(Exception, pps.loadPasswdTxt, 'a b\nc')
		# Transactional
		self.assertEquals(txt, pps.outputPasswdTxt())

		# load success
		pps.loadPasswdTxt('a b')
		self.assertEquals('b', pps.get('a'))
		pps.loadPasswdTxt('a1 b1\na2 b2')
		self.assertEquals('b1', pps.get('a1'))
		self.assertEquals('b2', pps.get('a2'))
		pps.loadPasswdTxt('e c d')
		self.assertEquals('e', pps.get('d'))

		# Overwrite.
		pps.loadPasswdTxt('a1 b3\na2 b2')
		self.assertEquals('b3', pps.get('a1'))
		self.assertEquals('b2', pps.get('a2'))
	def testLimit(self):
		pps = CheckSuperpass.getStore(limit=2)
		pps.append('b', 'x')
		for i in range(10):
			pps.append('a', '%d-pass'%i)
		self.assertEquals('8-pass 9-pass', pps.getHis('a'))
		self.assertEquals('x', pps.get('b'))
	def testGetSetAndReload(self):
		pps = CheckSuperpass.getStore()
		self.assertEquals([], pps.list())

		pps.append('a', 'ap')
		self.assertEquals(['a'], pps.list())
		self.assertEquals('ap', pps.get('a'))
		# site not exist yet
		self.assertRaises(Exception, pps.get, 'b')

		pps.append('b', 'bp')
		self.assertEquals(['a', 'b'], pps.list())
		self.assertEquals('ap', pps.get('a'))
		self.assertEquals('bp', pps.get('b'))
		self.assertEquals('ap', pps.getHis('a'))

		# overwrite
		pps.append('a', 'ap2')
		self.assertEquals(['a', 'b'], pps.list())
		self.assertEquals('ap2', pps.get('a'))
		self.assertEquals('bp', pps.get('b'))
		self.assertEquals('ap ap2', pps.getHis('a'))

def loadInternal():
	pps = PersonalPassStorage('', '')
	txt = """
"""
	pps.loadPasswdTxt(txt)
	pps.dump_to_disk()

if __name__ == '__main__':
	unittest.main()
	#loadInternal()
