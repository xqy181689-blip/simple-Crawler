from szreport.sz import SZ

sz = SZ()

# 以万科A为例，股票代码000002
urls = sz.pdfurls(code='000002')
for url in urls:
    print(url)
