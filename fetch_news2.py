import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
link = "https://news.google.com/rss/articles/CBMirAFBVV95cUxQd0ZBSHVSSGx0V0JpMnMtMWhHZEdDaGphX3dzYXlHM1BCUGxJTm9MTmxET2QyTG5WLTFUSDYzc2lIWk1tcGpkMWREWEt1djh1bTlkaVpfRGMyMzlZbFNXZzY3V2NmWE1FM1JXUnR2aDRNSFJ5WElxVGU5ajFpeVBYeVE1WlRKNnBmUGQ3RjdMMUFxcWJ0bWR6VG1SdkV3S2ZCRFZ3Y29IbEx5SXhX?oc=5"
res = requests.get(link, headers=headers)
print(res.text[:1000])
