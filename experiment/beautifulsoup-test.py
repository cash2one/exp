from bs4 import BeautifulSoup

html = open('/tmp/debug.html').read()
soup = BeautifulSoup(html, "html.parser")
#soup = BeautifulSoup(html, "lxml")
links = soup.find_all('a')
for l in links:
	print l
