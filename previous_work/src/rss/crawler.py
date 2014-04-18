import ascommon
import base64
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import time
from HTMLParser import HTMLParser

# TODO. move to common
def getPureTextInternal(soup):
	v = soup.string
	if v == None:
		c = soup.contents
		resulttext = ''
		for t in c:
			try:
				if t.name == 'script' or t.name == 'style':
					continue
			except Exception:
				pass
			subtext = getPureTextInternal(t)
			resulttext += subtext + '\n'
		return resulttext
	else:
		return v.strip()

def getPureText(soup):
	text = getPureTextInternal(soup)
	h = HTMLParser()
	return h.unescape(text)

class Crawler():
	def __init__(self, datadir = 'data'):
		self.__datadir = datadir

	def crawlUrl(self, url):
		filename = os.path.join(self.__datadir, 'crawled',
				self.__dst_filename(url, 'zhtml'))

		if os.path.isfile(filename):
			# already crawled
			print 'already exist', url
			return
		try:
			content = ascommon.CrawlOneUrl(url)
			time.sleep(1)
		except Exception as e:
			print 'crawl error for %s'%url, e
			return
		# save the content and checkpoint
		ascommon.zwrite(filename, content)

	def parseExistingDoc(self, url):
		""" for reprocess a document already crawled
		"""
		crawled_filename = os.path.join(self.__datadir, 'crawled',
				self.__dst_filename(url, 'zhtml'))
		if not os.path.isfile(crawled_filename):
			print 'not crawled for ', url
			return
		parsed_filename = os.path.join(self.__datadir, 'parsed',
				self.__dst_filename(url, 'txt'))
		if os.path.isfile(parsed_filename):
			print 'already parsed for ', url
			return
		print 'parsing for ', url, crawled_filename
		content = ascommon.zread(crawled_filename)
		# TODO. Make sure it's utf-8
		try:
			soup = BeautifulSoup(content)
			story = soup.find_all('div', {'class': 'story-body'})
			if len(story) < 1:
				return
			text = getPureText(story[0])
			of = open(parsed_filename, 'w')
			of.write(text)
			of.close()
		except Exception as e:
			print '\nCan not parse %s, \nERROR:'%url, e

	def __dst_filename(self, url, suffix):
		return '%s.%s'%(base64.b64encode(url, '-_'), suffix)

def handleFile(crawler, filename):
	for url in open(filename):
		#crawler.crawlUrl(url.strip())
		crawler.parseExistingDoc(url.strip())

def main():
	crawler = Crawler()
	found_dir = os.path.join('.', 'data', 'found')
	for filename in os.listdir(found_dir):
		handleFile(crawler, os.path.join(found_dir, filename))
		# TODO. remove the file in found_dir

if __name__ == '__main__':
	RUN_TEST = False
	if RUN_TEST:
		unittest.main()
	else:
		main()
