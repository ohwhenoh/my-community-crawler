import requests
import xml.etree.ElementTree as ET

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
rss_url = 'https://www.bing.com/news/search?q=LLM+security&format=rss'
res = requests.get(rss_url, headers=headers)
root = ET.fromstring(res.content)
for item in root.findall('.//item')[:2]:
    print("Title:", item.find('title').text)
    print("Link:", item.find('link').text)
