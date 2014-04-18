import urllib2
import os
from bs4 import BeautifulSoup
import pickle
import unittest
from datetime import datetime, timedelta

DEBUG = True

# TODO. replace with ascomon
def CrawlOneUrl(url):
	req = urllib2.Request(url)
	req.add_header('User-Agent', """Mozilla/5.0 (Mactintosh: Intel Mac OS X""")
	req.add_header('Accept', 'text/css,*/*;q=0.1')
	req.add_header('Accept-Charset', 'utf-8')
	req.add_header('Referrer', 'http://www.google.com/')
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

import zlib
# zread and zwrite provide simple way to read/write content with zip
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

	if DEBUG:
		dfile = open(filename + '.debug', 'w')
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

def Snippet(sentence, word, max_words):
	# TODO. lower case?
	words = sentence.strip('.').split(' ')
	if not word in words:
		print 'no word %s in sentence %s'%(word, sentence)
		end = len(sentence)
		if max_words < end:
			end = max_words
		return sentence[0:end]
	if len(words) <= max_words:
		return sentence
	m = words.index(word)
	start = m - (max_words / 2)
	if start < 0:
		start = 0
	end = start + max_words
	if end >= len(words):
		return ' '.join(words[start:])
	return ' '.join(words[start:end])

class TestSnippet(unittest.TestCase):
	def test_general(self):
		sentence = 'This is a unit test for snippet.'
		self.assertEqual('This is a', Snippet(sentence, 'This', 3))
		self.assertEqual('This is a unit test for', Snippet(sentence, 'This', 6))

		self.assertEqual('a unit test', Snippet(sentence, 'unit', 3))
		self.assertEqual('This is a unit test for', Snippet(sentence, 'unit', 6))

		self.assertEqual('for snippet', Snippet(sentence, 'snippet', 3))
		self.assertEqual('unit test for snippet', Snippet(sentence, 'snippet', 6))

class QueryHistory():
	"""
	TODO. add the related url as well.
	"""
	def __init__(self, his_limit = 100):
		# Snippets, keyed by snippet for dedupping, value is time and url
		# {snippet : {url: time} }
		# Note. url could be None. time is the lateset time user query.
		self.__snippets = {}
		# total number of queries
		self.__total_num = 0

	def AddUsage(self, snippet, url, ts):
		if snippet not in self.__snippets:
			# new one
			self.__snippets[snippet] = {url:ts}
		else:
			# existing, update last query time
			self.__snippets[snippet][url] = ts
		self.__total_num += 1

	def snippet(self):
		return self.__snippets
	def total_num(self):
		return self.__total_num

class TestQueryHistory(unittest.TestCase):
	def test_general(self):
		qs = QueryHistory(2)
		self.assertEqual(0, qs.total_num())
		
		now = datetime.now()
		day_1 = now + timedelta(days = 1)
		day_2 = now + timedelta(days = 2)

		qs.AddUsage('s0', 'url_now', now)
		self.assertEqual(now, qs.snippet()['s0']['url_now'])
		self.assertEqual(1, qs.total_num())

		qs.AddUsage('s1', 'url_1', day_1)
		self.assertEqual(2, len(qs.snippet()))
		self.assertEqual(now, qs.snippet()['s0']['url_now'])
		self.assertEqual(day_1, qs.snippet()['s1']['url_1'])
		self.assertEqual(2, qs.total_num())
		
		qs.AddUsage('s1', 'url_1', day_2)
		# duplicate will not add new snippet, but update time.
		self.assertEqual(2, len(qs.snippet()))
		self.assertEqual(now, qs.snippet()['s0']['url_now'])
		self.assertEqual(day_2, qs.snippet()['s1']['url_1'])
		self.assertEqual(3, qs.total_num())

class BaseProcessor:
	""" If not found in files, then crawl and extract the content.
			Save the content in the following format:
			word translation '\n'

			Storage:
			1. When crawled, will save to data/tmp/[query].html
			2. When processed, will save a entry in data/words.dict
			3. Also, user query history will be store in data/user.txt
	"""
	def __init__(self, channel, datadir):
		self.__datadir = datadir
		self.__tmpdir = os.path.join(datadir, 'tmp')
		# Not related to user. word -> translation. Make sure all lower case.
		# TODO. create separate classes, say TransDic, UserVisit.
		self.__translate = PersistDict(os.path.join(datadir, 'words.dict'))
		# TODO. per user data. word -> (snippet[], query_ts[],)
		self.__queries = PersistDict(os.path.join(datadir, '%s.user'%channel))
		# All uncatched query
		# TODO. Limit the length?
		# TODO. show the status in master page.
		self.__uncatched = PersistDict(os.path.join(datadir, 'uncatched.txt'))

	def DumpForQuery(self, query):
		""" return results:
				[query, translation, {snippet:{url:time}}]
		"""
		if not self.__queries.Has(query):
			print 'dump %s failed due to no query his'%query
			return []
		if not self.__translate.Has(query):
			print 'dump %s failed due to no translate'%query
			return []

		trans = self.__translate.Get(query)

		query_his = self.__queries.Get(query)
		snippet = query_his.snippet()

		return [query, trans, snippet]

	def DumpAllQuery(self):
		""" return results in:
				[[query, translation, {snippet:{url:time}}], ]
				TODO. [snippet, url, time]
		"""
		obj = []
		for k, v in self.__queries.mem().iteritems():
			out = self.DumpForQuery(k)
			if len(out) > 0:
				obj.append(out)
		return obj

	def Query(self, query, sentence, url = None):
		""" Give a query and sentence, return the translation
		    should not throw any exception
				the text returned is unicode
		"""
		# quick reject
		if len(query.split(' ')) > 1:
			print 'INVALID query ', query
			return "INVALID query"
		if len(query) > 50:
			print 'query TOO LONG', query
			return "Query too long"
		if self.__uncatched.Has(query):
			print 'Known invalid query ', query
			self.__uncatched.Set(query,	self.__uncatched.Get(query) + 1)
			return "NO RESULTS"
		# get translation
		translation = self.__get_translation(query)
		if translation is None:
			return "NO RESULTS"
		# Save record history
		self.__record_history(query, sentence, url)
		return '%s'%translation

	def url(self, query):
		assert 0
	def ExtractContent(self, doc_text):
		assert 0
	def __record_history(self, query, sentence, url):
		snippet = Snippet(sentence, query, 100)
		if self.__queries.Has(query):
			query_his = self.__queries.Get(query)
		else:
			query_his = QueryHistory()
		# TODO. Limit the sentence chars.
		query_his.AddUsage(snippet, url, datetime.now())
		self.__queries.Set(query, query_his)
	def __get_translation(self, q):
		# all lower case match.
		query = q.lower()
		# from existing dictionary
		if self.__translate.Has(query):
			print 'return from cache for ', query
			return self.__translate.Get(query)

		# recrawl if necessary
		crawl_tmp_file = os.path.join(self.__tmpdir, '%s.zhtml'%query)
		doc_text = ''
		need_write = False
		if not os.path.isfile(crawl_tmp_file):
			print 'Crawling for %s'%self.url(query)
			doc_text = CrawlOneUrl(self.url(query))
			need_write = True
		else:
			doc_text = zread(crawl_tmp_file)

		# Analyze and return results.
		trans = None
		try:
			trans = self.ExtractContent(doc_text)
		except Exception as e:
			print 'Can not extract for query ', query, e
			self.__uncatched.Set(query, 0)
			return None
		if trans is None or len(trans) <= 0:
			self.__uncatched.Set(query, 0)
			return None

		# translation are valid
		self.__translate.Set(query, '%s'%trans)
		if need_write:
			# Note. Only write for valid html, to avoid error pages
			zwrite(crawl_tmp_file, doc_text)
		return self.__translate.Get(query)


class YoudaoProcessor(BaseProcessor):
	def __init__(self, channel, datadir = 'youdaodata'):
		BaseProcessor.__init__(self, channel, datadir)

	def url(self, query):
		return 'http://dict.youdao.com/search?q=%s&ue=utf8'%query
	def ExtractContent(self, doc_text):
		content = AllocatePartialDoc(doc_text, '<div id="results-contents','<div id="webTrans')
		soup = BeautifulSoup(content)
		if DEBUG:
			print soup.prettify()
		t_container = soup.find_all("div", {"class": "trans-container"})
		txt = t_container[0].ul.li.text
		assert isinstance(txt, unicode)
		return txt.encode('utf-8')

def main():
	query = 'avatar'
	youdao = YoudaoProcessor()
	trans = youdao.Query(query, 'this is advantage case',
			'http://www.1.com')
	print asoutput(trans)
	trans = youdao.Query(query, 'this is another advantage case',
			'http://www.2.com')
	print youdao.DumpAllQuery()

if __name__ == '__main__':
	RUN_TEST = False
	if RUN_TEST:
		unittest.main()
	else:
		main()
