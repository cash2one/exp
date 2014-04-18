import feedparser

feedurl = "http://www.readwriteweb.com/rss.xml"
feed = feedparser.parse(feedurl)

for item in feed['entries']:
	print item.link, item.author

