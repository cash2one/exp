import collections
import timeit
import random
import urllib2
import time
import threading

from consumer_thread import Consumers, Producer, StoppableThread
from asbase import Logger, asoutput, WaitForCtrlC
from qps import QPS

import unittest

class Backoff():
	def __init__(self, init_s = 1, max_s = 60):
		self.__delay = init_s
		self.__max_s = max_s
	def Sleep(self):
		time.sleep(self.__delay)
		self.__delay = min(self.__delay * (1 + random.random()), self.__max_s)

class SimpleCrawler():
	def __init__(self, uacontent = 'Baiduspider'):
		self.__ua = uacontent
	def Crawl(self, url, timeout):
		""" Could throw IOError
		"""
		# TODO. urllib3 or httplib2 to reuse connection, also add a timeout
		req = urllib2.Request(url)
		req.add_header('User-Agent', self.__ua)
		req.add_header('Accept', 'text/css,*/*;q=0.1')
		req.add_header('Accept-Charset', 'utf-8')
		req.add_header('Referrer', 'http://www.baidu.com/')
		return urllib2.urlopen(req).read()

class AIMDQuota():
	""" Thread safe
	"""
	def __init__(self, init_quota, min_quota = 1, max_quota = 100):
		self.__lock = threading.RLock()
		self.__quota = init_quota
		self.__min_quota = min_quota
		self.__max_quota = max_quota
	def Get(self):
		self.__lock.acquire()
		n = self.__quota
		self.__lock.release()
		return n
	def Increase(self, inc):
		self.__lock.acquire()
		self.__quota = min(self.__max_quota, self.__quota + inc)
		self.__lock.release()
	def Decrease(self, dec):
		self.__lock.acquire()
		self.__quota = max(self.__min_quota, self.__quota - dec)
		self.__lock.release()
	def Divide(self):
		self.__lock.acquire()
		self.__quota = max(self.__min_quota, self.__quota / 2)
		self.__lock.release()

class ActiveRequest():
	def __init__(self):
		self.__lock = threading.RLock()
		self.__n = 0
	def Get(self):
		self.__lock.acquire()
		n = self.__n
		self.__lock.release()
		return n
	def Increase(self):
		self.__lock.acquire()
		self.__n += 1
		self.__lock.release()
	def Decrease(self):
		self.__lock.acquire()
		self.__n -= 1
		self.__lock.release()

class FixedArray():
	def __init__(self, l):
		self.__lock = threading.RLock()
		self.__q = collections.deque(maxlen = l)
	def Add(self, delay):
		self.__lock.acquire()
		self.__q.append(delay)
		self.__lock.release()
	def Clear(self):
		self.__lock.acquire()
		self.__q = collections.deque(maxlen = l)
		self.__lock.release()
	def full(self):
		self.__lock.acquire()
		left = self.__q.maxlen - len(self.__q) 
		self.__lock.release()
		return left == 0
	def Ave(self):
		self.__lock.acquire()
		s = 0
		for i in self.__q:
			s += i
		l = len(self.__q)
		if l > 0:
			ave = float(s) / l
			self.__lock.release()
			return ave

class AdaptiveCrawler():
	""" Make use of SimpleCrawler, but also consider the hostload.
	Will measure hostload at run time.
	For now, control purely based on window, I believe host latency is already included in concurrent window.

	The algorithm is based on AIMD:
	Every normal response back, window += 1
	If error qps > 3, window /= 2

	Before any request sent, make sure active_requests < window
	Each time a request sent, active_requests += 1
	Each time a response received, active_requests -= 1

	The problem is, we have only 100 threas, which means active request could be no more than 100. each request +1 window will be too aggressive. So we will consider latency as well.
	Keep track of 10*threads of latency, comparing current latency with average latency:
	- if latency increase, window -= 1
	- if latency decrease, window += 1
	"""
	def __init__(self, OnHtml, OnBusy, max_threads = 2,
			err_to_forget_in_s = 60, start_window = 20, uacontent = 'Baiduspider', LogFunc = None):
		self.__consumers = Consumers(self.__OnCrawlRequest, max_threads, max_threads + 5)
		self.__consumers.Start()
		self.__OnHtml = OnHtml
		self.__OnBusy = OnBusy
		self.__uacontent = uacontent
		self.__LogFunc = LogFunc

		self.__err_qps = QPS(err_to_forget_in_s)
		self.__err_qps_limit = 3
		self.__active_request = ActiveRequest()
		self.__window = AIMDQuota(start_window, start_window, max_threads)

		self.__crawler = SimpleCrawler(self.__uacontent)

	def Stop(self):
		self.__consumers.Stop()

	def Crawl(self, url, request = None):
		""" Request should include url, can also include some metadata
		"""
		self.__consumers.Feed([url, request])
	def __Log(self, msg, thread_name):
		if self.__LogFunc is None:
			return
		self.__LogFunc(msg, thread_name)

	def __OnCrawlRequest(self, thread_name, request, stopped):
		# Do we have enough bandwidth
		backoff = Backoff()
		while not stopped():
			aq = self.__active_request.Get()
			window = self.__window.Get()
			if aq <= window:
				break
			self.__Log('Lack of quota to crawl, %d VS %d, backoff sleep'%(aq, window), thread_name)
			backoff.Sleep()
		self.__active_request.Increase()
		url = request[0]
		params = request[1]
		start_ts = timeit.default_timer()
		try:
			html = self.__crawl(thread_name, url, 1)
		except IOError as e:
			self.__active_request.Decrease()
			eclipsed = timeit.default_timer() - start_ts
			self.__err_qps.Add()
			if self.__err_qps.Get() > self.__err_qps_limit:
				self.__window.Divide()
				self.__Log('quota to %.2f'%self.__window.Get(), thread_name)
			self.__OnBusy(thread_name, request, eclipsed)
		else:
			self.__active_request.Decrease()
			eclipsed = timeit.default_timer() - start_ts
			self.__window.Increase(1)
			self.__Log('quota to %.2f on delay %.2f'%(self.__window.Get(), eclipsed), thread_name)
			self.__OnHtml(thread_name, html, request, eclipsed)

	def __crawl(self, thread_name, url, timeout):
		return self.__crawler.Crawl(url, timeout)

def ExampleOnHtml(thread_name, html, crawl_request):
	print 'html for ', thread_name, crawl_request
def ExampleOnBusy(thread_name, crawl_request):
	print 'error for ', thread_name, crawl_request

class AdaptiveCrawlerTest(unittest.TestCase):
	def testBadHostLoad(self):
		self.assertEquals(0, 0)

class CrawlThread(StoppableThread):
	def __init__(self, crawler):
		super(CrawlThread, self).__init__()
		self.__crawler = crawler
	def run(self):
		for i in range(1000):
			if not self.stopped():
				self.__crawler.Crawl('http://%d.com'%i, i)

def main():
	crawler = AdaptiveCrawler(ExampleOnHtml, ExampleOnBusy)
	thread = CrawlThread(crawler)
	thread.start()
	WaitForCtrlC()
	print 'going to stop crawl thread'
	thread.Stop()
	print 'going to stop cralwer, with consumer thread'
	crawler.Stop()
	print 'all done'

if __name__ == '__main__':
	RUN_TEST = False
	if RUN_TEST:
		unittest.main()
	else:
		main()

