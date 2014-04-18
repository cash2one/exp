import feedparser

f = feedparser.parse("http://feeds.bbci.co.uk/news/rss.xml")

for item in f['entries']:
	print item.link

