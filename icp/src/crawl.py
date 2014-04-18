# TODO. keep track of data, error, busy files, and dump to log before quit.
# TODO. Only keep one province.txt, let user select province via flagfile
import fnmatch
import random
import urllib2
import os
from bs4 import BeautifulSoup
import unittest
import timeit
import threading
import hashlib

from consumer_thread import Consumers, StoppableThread
from ascrawl import AdaptiveCrawler
from asflagfile import Flagfile
from asbase import Logger, asoutput, WaitForCtrlC
from asfileutil import ExistsFile, CreateDirIfNotExists, DoOpenFile
from asstorage import KeyValueFileStorage

def ParseFlagfile():
	ff = Flagfile('flagfile.cfg')
	ff.AddInt('start_num', 0, 99999999)
	ff.AddInt('end_num', 0, 99999999)
	ff.AddInt('threads', 0, 5000)
	ff.AddInt('shard')
	ff.AddInt('max_shards')
	ff.AddInt('err_to_forget_in_s', 0, 3600)
	ff.AddInt('start_window', 0, 100)
	ff.AddString('ua_content')
	options = ff.Parse()
	assert options.shard < options.max_shards
	assert options.start_num < options.end_num
	assert options.start_window < options.threads
	return options, ff.ToString()

# fail count, at least 0.
# +1 for failed crawl, -1 for sucess crawl
class GlobalVariable:
	def __init__(self):
		pass
	def __del__(self):
		print 'Global Variable QUIT'
	def Main(self):
		# From flagfile
		self.options, ffname = ParseFlagfile()
		# province
		self.provinces = []
		for l in open('province-list.txt'):
			self.provinces.append(l.strip())
		# set up sub directories
		for i in range(0, len(self.provinces)):
			outfile = DoOpenFile(os.path.join('sample-output', '%d'%i, 'init'))
			outfile.close()
		# set up log file
		self.log = Logger(ffname, 'sample-output')
		print 'Run " tail -f %s " to see log file'%self.log.logfilename()
		# error storage to save files
		self.err_store = KeyValueFileStorage(os.path.join('sample-output', 'visited'), 1000, 60, True)

GV = GlobalVariable()

def LOG(log, thread_name = ''):
	GV.log.Log(log, thread_name)

def url1(num, pindex = 0):
	p = GV.provinces[pindex]
	suffix = urllib2.quote('%sICP\xe5\xa4\x87%08d\xe5\x8f\xb7'%(p, num))
	return 'http://www.beianbeian.com/search-1/%s'%suffix

def url2(num):
	return 'http://www.beianbeian.com/s?keytype=1&q=\xd4\xc1ICP\xb1\xb8%d\xba\xc5'%num


def ExtractMainPage(html):
	""" Extract data rows, return records
	if no records are extracted, len(records) = 0
	"""
	soup = BeautifulSoup(html)
	table = soup.find(id="show_table")
	if table == None:
		return []
	trs = table.find_all("tr")
	n = len(trs)
	extract_rows = []
	for i in range(1, n):
		tds = trs[i].find_all("td")
		if len(tds) < 6:
			continue

		td_txts = []
		for td in tds:
			td_txts.append(td.get_text().strip())

		l = trs[i].find_all('a')
		if len(l) > 0:
			detail_url = l[-1].get('href').strip()
			td_txts.append(detail_url)
		extract_rows.append(td_txts)
	return extract_rows

class ICPStorage():
	def __init__(self, directory, num, pindex):
		""" pindex stand for province index
		"""
		self.__directory = directory
		self.__num = num
		self.__pindex = pindex
	def HasData(self, search_all_index = False):
		""" Assumption, ICP are unique among all province. If one province have data, no need to search in another province.
		"""
		if not search_all_index:
			return ExistsFile(self.__datafilename(self.__pindex))
		for pindex in range(0, len(GV.provinces)):
			if ExistsFile(self.__datafilename(pindex)):
				return True
		return False
	def StoreData(self, data):
		outfile = DoOpenFile(self.__datafilename(self.__pindex))
		outfile.write(data)
		outfile.close()
	def HasError(self):
		return GV.err_store.Has(self.__errkey())
	def StoreError(self, data):
		GV.err_store.Set(self.__errkey(), data)
	def StoreBusy(self, data):
		GV.err_store.Set(self.__busykey(), data)
	def __errkey(self):
		return '%d:%d'%(self.__num, self.__pindex)
	def __busykey(self):
		return '%d:%d:busy'%(self.__num, self.__pindex)
	def __datafilename(self, pindex):
		return self.__suffixfilename(pindex, 'data')
	def __suffixfilename(self, pindex, suffix):
		return os.path.join(self.__directory, '%d'%pindex, '%d.%s'%(self.__num, suffix))

def ShouldProcess(num):
	if GV.options.max_shards == 0:
		return True

	s = hashlib.sha224('fix seed to make sure repeatable %d'%num).hexdigest()
	n = int(s, 16)
	return n % GV.options.max_shards == GV.options.shard

def OnHtml(thread_name, html, crawl_request, eclipsed):
	url = crawl_request[0]
	params = crawl_request[1]
	num = params[0]
	pindex = params[1]

	extract_rows = ExtractMainPage(html)
	LOG('found %d records in %.2f seconds when crawl %s'%(len(extract_rows), eclipsed, url),
			thread_name)
	# store
	storage = ICPStorage('sample-output', num, pindex)
	if len(extract_rows) > 0:
		data = ''
		for row in extract_rows:
			s = '\n'.join(row)
			data += asoutput(s)
			data += '\n\n'
		storage.StoreData(data)
		return True
	else:
		storage.StoreError('%s %.2f seconds'%(url, eclipsed))
		return False

def OnBusy(thread_name, crawl_request, eclipsed):
	url = crawl_request[0]
	params = crawl_request[1]
	num = params[0]
	pindex = params[1]
	storage = ICPStorage('sample-output', num, pindex)
	storage.StoreBusy('%s %.2f seconds'%(url, eclipsed))


class CrawlThread(StoppableThread):
	def __init__(self, crawler):
		super(CrawlThread, self).__init__()
		self.__crawler = crawler
	def run(self):
		start = timeit.default_timer()
		pindexs = list(range(0, len(GV.provinces)))
		random.shuffle(pindexs)
		for pindex in pindexs:
			a = random.randint(GV.options.start_num, GV.options.end_num)
			for i in range(0, GV.options.end_num - GV.options.start_num):
				if self.stopped():
					break
				num = GV.options.start_num + (a + i) % (GV.options.end_num - GV.options.start_num)
				# sample
				if not ShouldProcess(num):
					continue
				# alrady exist?
				storage = ICPStorage('sample-output', num, pindex)
				if storage.HasData() or storage.HasError():
					LOG('Skip existing num %d'%num, 'CrawlThread')
					continue
				# feed
				self.__crawler.Crawl(url1(num, pindex), [num, pindex])
		eclipsed = timeit.default_timer() - start
		print 'Quit sending numbers after %.2f seconds'%eclipsed

def OnCtrlC(signal, frame):
	print 'Please wait for a while, system will shutdown soon'

def try_one():
	# normal
	num = 12005810
	# unicode
	num = 12005839
	# no records
	num = 13005888
	# two records
	num = 12005838
	# multiple urls
	num = 12005888
	# three records
	num = 10000002
	ProcessOneNum(num)

def main():
	print 'Welcome to Crawl!'
	allfiles = [f for f in os.listdir('sample-output') if os.path.isfile(os.path.join('sample-output', f))]
	for f in allfiles:
		if fnmatch.fnmatch(f, '*.lock'):
			print 'sample-output/%s MUST BE REMOVED BEFORE CONTINUE'%f
			return
	print 'Press Ctrl+C to quit properly, or next run will hung'
	GV.Main()
	# TODO: ua
	crawler = AdaptiveCrawler(OnHtml, OnBusy,	GV.options.threads,
			GV.options.err_to_forget_in_s, GV.options.start_window,
			GV.options.ua_content, LOG)
	thread = CrawlThread(crawler)
	thread.start()
	WaitForCtrlC(OnCtrlC)
	print 'going to stop crawl thread'
	thread.Stop()
	print 'wait for crawl thread join'
	thread.join()
	print 'going to stop cralwer, with consumer thread'
	crawler.Stop()
	print 'all done'

if __name__ == '__main__':
	RUN_TEST = False
	if RUN_TEST:
		unittest.main()
	else:
		main()
		# try_one()
