# szreport

A 股上市公司定期报告批量下载工具，数据源为巨潮资讯网（cninfo.com.cn）。

支持**深交所、上交所、北交所**全部 A 股上市公司的年报、半年报、一季报、三季报的查询与下载。

## 安装

```bash
cd szreport
pip install -e .
```

## 快速开始

```python
from szreport.sz import SZ

sz = SZ()

# 下载万科A近10年所有定期报告
sz.download(code='000002', savepath='.')

# 只下载年报
sz.download(code='000002', savepath='.', report_types=['年报'])
```

## API 说明

### `SZ(cookies=None)`

初始化客户端，通常不需要传入 cookies。

### `sz.companys()`

获取深交所所有 A 股上市公司名录。

```python
df = sz.companys()
# 返回 DataFrame，包含 name（公司名）和 code（股票代码）两列
```

### `sz.disclosure(code, report_types=None)`

获取指定公司的定期报告披露信息，返回 DataFrame。

```python
# 获取所有定期报告信息
df = sz.disclosure(code='000002')

# 只获取年报
df = sz.disclosure(code='000002', report_types=['年报'])

# 获取年报和半年报
df = sz.disclosure(code='000002', report_types=['年报', '半年报'])
```

返回的 DataFrame 包含以下列：

| 列名 | 说明 |
|------|------|
| company | 报告标题 |
| code | 股票代码 |
| date | 披露日期 |
| pdf | PDF 下载链接 |

### `sz.pdfurls(code, report_types=None)`

获取指定公司定期报告的 PDF 下载链接列表。

```python
urls = sz.pdfurls(code='000002', report_types=['年报'])
```

### `sz.download(code, savepath, report_types=None)`

下载指定公司的定期报告 PDF 文件。

```python
sz.download(code='000002', savepath=r'D:\财报', report_types=['年报'])
```

- 文件保存路径：`{savepath}/disclosure/szreports/{code}/`
- 已存在的文件会自动跳过，支持断点续传
- 自动过滤摘要、英文版、正文版（保留全文版）、已取消的报告

### `sz.date_ranges(years=10)`

生成查询的日期范围，默认回溯 10 年。

### `report_types` 参数

| 值 | 说明 |
|------|------|
| `None` | 所有定期报告（年报+半年报+一季报+三季报） |
| `['年报']` | 仅年度报告 |
| `['半年报']` | 仅半年度报告 |
| `['一季报']` | 仅第一季度报告 |
| `['三季报']` | 仅第三季度报告 |

可组合使用，如 `['年报', '半年报']`。

## 交易所支持

根据股票代码自动识别交易所：

| 代码前缀 | 交易所 |
|----------|--------|
| 00、30 | 深交所 |
| 60、68 | 上交所 |
| 8、4 | 北交所 |

## 使用示例

### 批量下载深交所年报

```python
from szreport.sz import SZ
from tqdm import tqdm
import time

sz = SZ()
df = sz.companys()
df = df[df['code'].str.match(r'^(00|30)')]

for code in tqdm(df['code'], desc="下载进度"):
    try:
        sz.download(code=code, savepath=r'D:\财报', report_types=['年报'])
    except Exception as e:
        print(f"\n{code} 下载失败: {e}")
    time.sleep(0.5)
```

### 批量下载上交所年报

```python
from szreport.sz import SZ
from tqdm import tqdm
import time

sz = SZ()
df = sz.companys()
df = df[df['code'].str.match(r'^(60|68)')]

for code in tqdm(df['code'], desc="下载进度"):
    try:
        sz.download(code=code, savepath=r'D:\财报', report_types=['年报'])
    except Exception as e:
        print(f"\n{code} 下载失败: {e}")
    time.sleep(0.5)
```

### 导出披露信息到 Excel

```python
from szreport.sz import SZ

sz = SZ()
df = sz.disclosure(code='000002', report_types=['年报'])
df.to_excel('万科A年报信息.xlsx', index=False)
```

## 项目结构

```
szreport/
├── setup.py                # 安装配置
├── README.md               # 项目说明
├── szreport/
│   ├── __init__.py
│   └── sz.py               # 核心模块
└── test/
    ├── 深交所下载.py         # 批量下载深交所报告
    ├── 上交所下载.py         # 批量下载上交所报告
    ├── 获取上市公司目录.py    # 获取上市公司名录
    ├── 获取上市公司披露日期等信息.py
    └── 获取某公司的所有定期报告url.py
```

## 依赖

- Python >= 3.7
- requests
- pandas
