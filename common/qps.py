import time
import unittest
import threading

class QPS():
	""" QPS calculator, thread safe
	"""
	def __init__(self, window = 1):
		self.__lock = threading.RLock()
		self.__q = []
		# window in seconds
		self.__window = window
		# To improve performance, remove dead one in window switch.
		self.__last_time = 0
	def Get(self):
		"""Get current qps
		"""
		self.__lock.acquire()
		self.__remove_dead_items()
		l = len(self.__q)
		self.__lock.release()
		return l
	def Add(self):
		"""
		"""
		self.__lock.acquire()
		t = self._GetTime()
		l = len(self.__q)
		if l > 0:
			assert self.__q[l - 1] < t
		self.__q.append(t)
		removed = self.__remove_dead_items()
		self.__lock.release()
		return removed
	def CurrentEpoch(self):
		self.__lock.acquire()
		t = self.__last_time
		self.__lock.release()
		return t

	def _GetTime(self):
		return time.time()
	def __remove_dead_items(self):
		current_t = self._GetTime()
		if current_t < self.__window + self.__last_time:
			# time is not up.
			return False
		self.__last_time = current_t

		nq = []
		for t in self.__q:
			if t + self.__window > current_t:
				nq.append(t)
		self.__q = nq
		return True

class AdaptiveCrawlerTest(unittest.TestCase):
	def testBadHostLoad(self):
		qps = QPS(0.5)
		self.assertEquals(0, qps.Get())
		qps.Add()
		self.assertEquals(1, qps.Get())
		qps.Add()
		qps.Add()
		self.assertEquals(3, qps.Get())
		time.sleep(0.2)
		qps.Add()
		self.assertEquals(4, qps.Get())
		time.sleep(0.3)
		qps.Add()
		self.assertEquals(2, qps.Get())
		time.sleep(0.2)
		self.assertEquals(1, qps.Get())
		time.sleep(0.3)
		self.assertEquals(0, qps.Get())

def main():
	pass

if __name__ == '__main__':
	RUN_TEST = True
	if RUN_TEST:
		unittest.main()
	else:
		main()

