import pickle
import os
import time
import threading
from datetime import datetime

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
	return d

class PersistDict():
	"""Not thread safe
	"""
	def __init__(self, filename, auto_flush = True):
		self.__filename = filename
		self.__auto_flush = auto_flush

		if os.path.isfile(filename):
			pk_file = open(filename, 'rb')
			self._mem = pickle.load(pk_file)
			pk_file.close()
		else:
			self._mem = {}

	def Has(self, k):
		return k in self._mem
	def Get(self, k):
		return self._mem[k]
	def Set(self, k, v):
		self._mem[k] = v
		if self.__auto_flush:
			self.Flush()
	def Flush(self):
		outfp = open(self.__filename, 'wb+')
		pickle.dump(self._mem, outfp)
		outfp.close()
	
	def iterkeys(self):
		return self._mem.iterkeys()
	def length(self):
		return len(self._mem)
	
	def __str__(self):
		out = 'total items:%d\n'%len(self._mem)
		all_items = [ '%s %s'%(k, v) for (k, v) in self._mem.iteritems() ]
		return out + '\n'.join(all_items)

def TryLockfile(filename):
	try:
		f = open(filename, 'r')
		f.close()
		return False
	except IOError:
		# file not exists, get lock
		# Small chance that, two guy try to write the same lock
		f = open(filename, 'w')
		f.close()
		return True
def TryRemoveLock(filename):
	os.remove(filename)
		
class KeyValueFileStorage():
	""" Thread safe key value storage.
	Make use of PersistDict and queue to implement.
	Will acquire a lock in file before using it
	"""
	def __init__(self, filename,
			flush_every_n = 100, flush_delay = 1,
			acquire_filelock = False):
		self.__filename = filename
		self.__lockfilename = filename + '.lock'
		self.__flush_every_n = flush_every_n
		self.__flush_delay = flush_delay
		self.__acquire_filelock = acquire_filelock
		# acquire .lock
		while acquire_filelock:
			if TryLockfile(self.__lockfilename):
				break
			time.sleep(1)

		self.__storelock = threading.RLock()
		self.__store = PersistDict(filename, False)
		self.__pending_count = 0
		self.__last_flush_time = datetime.now()

	def __del__(self):
		self.__Flush()
		if self.__acquire_filelock:
			TryRemoveLock(self.__lockfilename)

	def Set(self, k, v):
		"""None blocking becuase it may be accessed by many threads.
		small chance you will lose data because data are flushed based on time and volume.
		"""
		if not self.__acquire_filelock:
			print 'not allowed to Set without having a filelock'
			return
		self.__storelock.acquire()
		self.__store.Set(k, v)
		self.__pending_count += 1
		if self.__ShouldFlush():
			self.__Flush()
		self.__storelock.release()
	def Has(self, k):
		self.__storelock.acquire()
		has = self.__store.Has(k)
		self.__storelock.release()
		return has
	def Get(self, k):
		self.__storelock.acquire()
		v = self.__store.Get(k)
		self.__storelock.release()
		return v
	def iterkeys(self):
		return self.__store.iterkeys()
	def length(self):
		return self.__store.length()

	def __ShouldFlush(self):
		if self.__pending_count >  self.__flush_every_n:
			return True
		eclipsed = datetime.now() - self.__last_flush_time
		if eclipsed.total_seconds() > self.__flush_delay:
			return True
		# TODO: On time
		return False
	def __Flush(self):
		if not self.__acquire_filelock:
			print 'CAN NOT FLUSH WITHOUT filelock'
			return
		if self.__pending_count > 0:
			self.__store.Flush()
			self.__pending_count = 0
			self.__last_flush_time = datetime.now()

def main():
	kvstore = KeyValueFileStorage('kvstore.data', 10, 3)
	for i in range(20):
		kvstore.Set('name-%d'%i, i)
		time.sleep(0.1)
	del kvstore

if __name__ == '__main__':
	main()
	print 'main finish'
