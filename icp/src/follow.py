def ExtractDetailPage(html):
	domains = []
	soup = BeautifulSoup(html)
	links = soup.find_all('a')
	for link in links:
		url = link.get('href')
		if url == None:
			continue
		prefix = '/go/?domain='
		if len(url) > len(prefix) and url.find(prefix) == 0:
			domains.append(url[len(prefix) :])
	return '\n'.join(domains)



def foo():
		l = trs[i].find_all('a')
		if len(l) > 0:
			detail_url = l[-1].get('href').strip()
			td_txts.append(detail_url)
			# follow detail url
			if GV.follow:
				detail_html = CrawlOneUrl("http://www.beianbeian.com" + detail_url)
				domain = ExtractDetailPage(detail_html)
				td_txts.append(domain)

