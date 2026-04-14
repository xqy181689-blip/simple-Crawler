from szreport.sz import SZ

sz = SZ()

# 以万科A为例，股票代码000002
df = sz.disclosure(code='000002')
print(df)

# 只获取年报
# df = sz.disclosure(code='000002', report_types=['年报'])

# 将查询结果存储
# df.to_excel('万科A定期报告信息.xlsx')
