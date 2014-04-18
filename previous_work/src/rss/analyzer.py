import os
import base64

class WordArticle:
	def __init__(self):
		# {word : {article_url:count} }
		self.__word_article = {}
	def handleArticle(self, content, url):
		for line in content.split('\n'):
			s = line.strip().lower()
			if len(s) < 1:
				continue
			for word in s.split():
				cleaned = word.strip(',.;?:!"\'|')
				if len(cleaned) < 1:
					continue
				if not self.__is_pure_word(cleaned):
					# remove digit, url and others
					continue
				if cleaned not in self.__word_article:
					# first time to see such word
					self.__word_article[cleaned] = {url:0}
				if url not in self.__word_article[cleaned]:
					# first time to see such word in this article
					self.__word_article[cleaned][url] = 0
				self.__word_article[cleaned][url] += 1
	def getSuggestArticle(self, new_words):
		""" Given a list of new words, return one suggest article
		"""
		# uni_count. number of new_words in an article.

		# all (url, word) pair which include new_words
		# { url: uniq words }
		uni_count = {}
		for new_word in new_words:
			if new_word in self.__word_article:
				for url in self.__word_article[new_word].iterkeys():
					# now it's a unique (new_word, url) pair, counting on each url
					if url not in uni_count:
						uni_count[url] = 0
					uni_count[url] += 1

		# Find the max one
		max_count = 0
		max_url = ''
		for url, count in uni_count.iteritems():
			if count > max_count:
				max_count = count
				max_url = url
		return (max_url, max_count)

	def __is_pure_word(self, word):
		s = word.lower()
		for ch in s:
			if ch < 'a' or ch > 'z':
				return False
		return True

	def __str__(self):
		out = []
		total_words = 0
		for word, url_count in self.__word_article.iteritems():
			urls = ' '.join([ url for url, count in url_count.iteritems()])
			out.append('%s %s'%(word, urls))
			total_words += 1
		out.append('total words: %d'%total_words)
		return '\n'.join(out)

def main():
	word_article = WordArticle()
	parsed_dir = os.path.join('data', 'parsed')
	for filename in os.listdir(parsed_dir):
		no_suffix = '.'.join(filename.split('.')[:-1])
		url = base64.b64decode(no_suffix, '-_')
		inf = open(os.path.join(parsed_dir, filename), 'r')
		word_article.handleArticle(inf.read(), url)
		inf.close()
	#print word_article
	print word_article.getSuggestArticle(['whale', 'tradition', 'notwac', 'annet'])

if __name__ == '__main__':
	RUN_TEST = False
	if RUN_TEST:
		unittest.main()
	else:
		main()
