import os
import pickle
import random, string
import time
import unittest
import urllib2
import zlib

def rand_string(N = 30):
	return ''.join(random.choice(string.ascii_uppercase + string.digits)
								 for x in range(N))

class ExpireObjectExpired(Exception):
	def __init__(self):
		pass
	def __str__(self):
		return 'object expired'

class ExpireObject():
	def __init__(self, expire_sec):
		self.__expiration = time.time() + expire_sec

	def __str__(self):
		return str(self.__expiration)

	def CheckValid(self):
		if time.time() >= self.__expiration:
			raise ExpireObjectExpired()

# Store
class StoreException(Exception):
	def __init__(self, err):
		self.err = err
	def __str(self):
		return self.err

class MemStore():
	def __init__(self):
		self.dic = {}
	def read(self, name):
		if name not in self.dic:
			raise StoreException('no mem result for %s'%name)
		return self.dic[name]
	def write(self, name, msg):
		self.dic[name] = msg

class FileStore():
	def read(self, name):
		try:
			return open(name, 'r').read()
		except IOError:
			raise StoreException('Can not open file %s'%name)
	def write(self, name, msg):
		open(name, 'w').write(msg)

class CheckStore(unittest.TestCase):
	def testAsMemStore(self):
		store = MemStore()
		self.assertRaises(StoreException, store.read, 'a')
		store.write('a', 'ma')
		self.assertEquals('ma', store.read('a'))
		store.write('b', 'mb')
		self.assertEquals('mb', store.read('b'))
		self.assertRaises(StoreException, store.read, 'c')

import hashlib,base64

def shortReadableName(str):
	""" filename and url safe, use - and _.
	"""
	m = hashlib.md5()
	m.update(str)
	return base64.urlsafe_b64encode(m.digest())

# TODO. remove dup in translate.py
def CrawlOneUrl(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', """Mozilla/8.1 (Mactintosh: Intel Mac OS X""")
	req.add_header('Accept', 'text/css,*/*;q=0.1')
	req.add_header('Accept-Charset', 'utf-8')
	req.add_header('Referrer', 'http://www.google.com/reader')
	print 'crawling ', url
	return urllib2.urlopen(req).read()

def AllocatePartialDoc(content, start, end):
	partial_doc = ""
	found_start = False
	lines = content.split('\n')
	for line in lines:
		if line.find(start) >= 0:
			found_start = True
		if found_start:
			if line.find(end) >= 0:
				break
			partial_doc += line
	return partial_doc

def asoutput(str):
	if isinstance(str, unicode):
		print str.encode('gb2312')
	else:
		print str.decode('utf-8').encode('gb2312')

def zwrite(filename, d):
	c = zlib.compress(d)
	outfile = open(filename, 'wb+')
	outfile.write(c)
	outfile.close()

def zread(filename):
	infile = open(filename, 'rb')
	c = infile.read()
	d = zlib.decompress(c)
	infile.close()

	DEBUG = False
	if DEBUG:
		dfile = open(filename + '.debug.html', 'w')
		dfile.write(d)
		dfile.close()
	return d

class PersistStorageBase:
	""" persist storage base class.
	    every changes in list are persist
	"""
	def __init__(self, filename, mem):
		self.__filename = filename

		if os.path.isfile(filename):
			pk_file = open(filename, 'rb')
			self._mem = pickle.load(pk_file)
			pk_file.close()
		else:
			self._mem = mem

	def mem(self):
		return self._mem

	def _out(self):
		outfp = open(self.__filename, 'wb+')
		pickle.dump(self._mem, outfp)
		outfp.close()

class PersistDict(PersistStorageBase):
	def __init__(self, filename):
		PersistStorageBase.__init__(self, filename, {})

	def Has(self, k):
		return k in self._mem
	def Get(self, k):
		return self._mem[k]
	def Set(self, k, v):
		self._mem[k] = v
		self._out()
	
	def __str__(self):
		out = 'total items:%d\n'%len(self._mem)
		all_items = [ '%s %s'%(k, v) for (k, v) in self._mem.iteritems() ]
		return out + '\n'.join(all_items)

if __name__ == '__main__':
	unittest.main()
