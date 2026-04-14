from szreport.sz import SZ

sz = SZ()
df = sz.companys()

# 显示前5条数据
print(df.head())

# 将查询结果存储
df.to_excel('深交所上市公司名录.xlsx')
