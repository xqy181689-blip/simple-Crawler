#!/usr/bin/env python3
# 深交所上市公司定期报告下载工具（数据源：巨潮资讯网）

import re
import random
import time
import pandas as pd
import requests
import datetime
import json
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

REPORT_TYPES = {
    '年报': ['年度报告', '年报'],
    '半年报': ['半年度报告', '半年报', '中期报告'],
    '一季报': ['第一季度报告', '一季度报告', '一季报'],
    '三季报': ['第三季度报告', '三季度报告', '三季报'],
}

_CATEGORY_MAP = {
    '年报': 'category_ndbg_szsh',
    '半年报': 'category_bndbg_szsh',
    '一季报': 'category_yjdbg_szsh',
    '三季报': 'category_sjdbg_szsh',
}

_CNINFO_ANN_URL = 'https://www.cninfo.com.cn/new/hisAnnouncement/query'
_CNINFO_SEARCH_URL = 'https://www.cninfo.com.cn/new/information/topSearch/query'
_CNINFO_PDF_BASE = 'https://static.cninfo.com.cn/'
_STOCK_LIST_URL = 'https://www.cninfo.com.cn/new/data/szse_stock.json'


def _parse_cookies(cookie_input):
    """将 cookie 字符串或旧格式 dict 解析为标准 dict"""
    if isinstance(cookie_input, str):
        raw = cookie_input
    elif isinstance(cookie_input, dict):
        raw = cookie_input.get('Cookie', cookie_input.get('cookie', ''))
        if not raw:
            return cookie_input
    else:
        return cookie_input or {}
    result = {}
    for item in raw.split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            result[k.strip()] = v.strip()
    return result


class SZ(object):
    def __init__(self, cookies=None):
        """
        :param cookies: cookie字符串或dict，通常不需要
        """
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.cninfo.com.cn/new/disclosure/stock',
            'Accept': 'application/json',
        })
        if cookies:
            parsed = _parse_cookies(cookies)
            self._session.cookies.update(parsed)
        self._org_id_cache = {}

    def _request_with_retry(self, method, url, max_retries=3, **kwargs):
        """带重试的请求"""
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    resp = self._session.get(url, **kwargs)
                else:
                    resp = self._session.post(url, **kwargs)
                return resp
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 * (attempt + 1)
                    print(f'        请求失败，{wait}秒后重试({attempt+1}/{max_retries}): {e}')
                    time.sleep(wait)
                else:
                    raise

    @staticmethod
    def _detect_exchange(code):
        """根据股票代码判断交易所，返回 (column, plate)"""
        code = str(code)
        if code.startswith(('60', '68')):
            return 'sse', 'sh'
        if code.startswith(('8', '4')):
            return 'bj', 'bj'
        return 'szse', 'sz'

    def _get_org_id(self, code):
        """通过巨潮搜索接口获取 orgId"""
        if code in self._org_id_cache:
            return self._org_id_cache[code]
        resp = self._request_with_retry('POST', _CNINFO_SEARCH_URL,
            data={'keyWord': str(code), 'maxSecNum': 10, 'maxListNum': 5},
            timeout=15)
        data = resp.json()
        if isinstance(data, list) and data:
            org_id = data[0].get('orgId', '')
            self._org_id_cache[code] = org_id
            return org_id
        return ''

    def _match_report_type(self, title, report_types=None):
        """根据标题判断是否属于指定的报告类型，排除摘要、英文版和正文版（保留全文版）"""
        if '摘要' in title:
            return False
        if '英文版' in title:
            return False
        if '正文' in title:
            return False
        if '已取消' in title:
            return False
        if report_types is None:
            return True
        half_year_kws = REPORT_TYPES['半年报']
        is_half_year = any(kw in title for kw in half_year_kws)
        for rt in report_types:
            if rt == '年报' and is_half_year:
                continue
            keywords = REPORT_TYPES.get(rt, [rt])
            if any(kw in title for kw in keywords):
                return True
        return False

    def _query_announcements(self, code, category='', begin_date='', end_date='', page_num=1, page_size=30):
        """查询巨潮资讯网公告列表"""
        org_id = self._get_org_id(code)
        stock_param = f'{code},{org_id}' if org_id else str(code)
        se_date = f'{begin_date}~{end_date}' if begin_date and end_date else ''
        column, plate = self._detect_exchange(code)
        resp = self._request_with_retry('POST', _CNINFO_ANN_URL,
            data={
                'stock': stock_param,
                'tabName': 'fulltext',
                'column': column,
                'plate': plate,
                'pageNum': page_num,
                'pageSize': page_size,
                'category': category,
                'seDate': se_date,
                'searchkey': '',
                'secid': '',
                'sortName': '',
                'sortType': '',
                'isHLtitle': 'true',
            },
            timeout=30)
        return resp.json()

    def date_ranges(self, years=10):
        """
        :param years: 往前追溯的年数，默认10年
        """
        now = datetime.datetime.today()
        begin = now - datetime.timedelta(days=years * 365)
        return begin.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')

    def companys(self):
        """
        深交所所有A股上市公司名录，公司名及股票代码
        :return: 返回DataFrame
        """
        try:
            resp = self._request_with_retry('GET', _STOCK_LIST_URL, timeout=30)
            data = resp.json()
            stocks = []
            stock_list = data.get('stockList', [])
            for item in stock_list:
                code = item.get('code', '')
                name = item.get('zwjc', '')
                org_id = item.get('orgId', '')
                if code:
                    stocks.append([name, code])
                    if org_id:
                        self._org_id_cache[code] = org_id
            df = pd.DataFrame(stocks, columns=['name', 'code'])
            return df
        except Exception:
            print('cninfo股票列表获取失败，尝试备用方式...')
            return self._companys_from_search()

    def _companys_from_search(self):
        """备用方式：通过搜索接口获取股票列表（较慢）"""
        resp = self._request_with_retry('POST', _CNINFO_SEARCH_URL,
            data={'keyWord': '', 'maxSecNum': 5000, 'maxListNum': 0},
            timeout=30)
        data = resp.json()
        stocks = []
        if isinstance(data, list):
            for item in data:
                if item.get('category') == 'A股':
                    code = item.get('code', '')
                    name = item.get('zwjc', '')
                    if code:
                        stocks.append([name, code])
        return pd.DataFrame(stocks, columns=['name', 'code'])

    def disclosure(self, code, report_types=None):
        """
        获得该公司的报告标题、股票代码、披露日期、PDF下载链接，返回DataFrame。
        :param code: 股票代码
        :param report_types: 筛选报告类型，如 ['年报'] 或 ['年报','半年报']，None则获取所有定期报告
        :return: 返回DataFrame
        """
        print('正在获取{}定期报告披露信息'.format(code))
        begin_date, end_date = self.date_ranges()
        category = self._build_category(report_types)
        datas = []
        page = 1
        while True:
            result = self._query_announcements(code, category, begin_date, end_date, page_num=page)
            announcements = result.get('announcements') or []
            if not announcements:
                break
            for ann in announcements:
                title = ann.get('announcementTitle', '')
                adj_url = ann.get('adjunctUrl', '')
                if not adj_url:
                    continue
                pdf_url = _CNINFO_PDF_BASE + adj_url
                if not self._match_report_type(title, report_types):
                    continue
                pub_time = ann.get('announcementTime', 0)
                if pub_time:
                    pub_date = datetime.datetime.fromtimestamp(pub_time / 1000).strftime('%Y-%m-%d')
                else:
                    pub_date = ''
                sec_code = ann.get('secCode', str(code))
                data = [title, str(sec_code), pub_date, pdf_url]
                datas.append(data)
            if not result.get('hasMore', False):
                break
            page += 1
        df = pd.DataFrame(datas, columns=['company', 'code', 'date', 'pdf'])
        return df

    def _build_category(self, report_types):
        """将 report_types 转换为巨潮 API 的 category 参数"""
        if not report_types:
            categories = list(_CATEGORY_MAP.values())
            return ';'.join(categories)
        cats = []
        for rt in report_types:
            if rt in _CATEGORY_MAP:
                cats.append(_CATEGORY_MAP[rt])
        return ';'.join(cats) if cats else ''

    def pdfurls(self, code, report_types=None):
        """
        获取定期报告pdf下载链接
        :param code: 股票代码
        :param report_types: 筛选报告类型，如 ['年报'] 或 ['年报','半年报']，None则获取所有定期报告
        :return: PDF链接列表
        """
        type_desc = '、'.join(report_types) if report_types else '所有定期报告'
        print('准备获取{} [{}] 文件链接'.format(code, type_desc))
        begin_date, end_date = self.date_ranges()
        category = self._build_category(report_types)
        urls = []
        page = 1
        while True:
            result = self._query_announcements(code, category, begin_date, end_date, page_num=page)
            announcements = result.get('announcements') or []
            if not announcements:
                break
            for ann in announcements:
                title = ann.get('announcementTitle', '')
                adj_url = ann.get('adjunctUrl', '')
                if not adj_url:
                    continue
                if self._match_report_type(title, report_types):
                    urls.append(_CNINFO_PDF_BASE + adj_url)
            if not result.get('hasMore', False):
                break
            page += 1
        print('        找到{}个PDF链接'.format(len(urls)))
        return urls

    def download(self, code, savepath, report_types=None):
        """
        下载该公司（code）的定期报告pdf文件
        :param code: 上市公司股票代码
        :param savepath: 数据存储所在文件夹的路径
        :param report_types: 筛选报告类型，如 ['年报'] 或 ['年报','半年报']，None则下载所有定期报告
        """
        path = Path(savepath).joinpath(*('disclosure', 'szreports', str(code)))
        Path(path).mkdir(parents=True, exist_ok=True)

        urls = self.pdfurls(code=code, report_types=report_types)
        if not urls:
            print('未找到符合条件的报告')
            return

        success, fail, skip = 0, 0, 0
        for url in urls:
            pdfname = url.split('/')[-1]
            pdfpath = path.joinpath(pdfname)
            if pdfpath.exists():
                skip += 1
                continue
            try:
                resp = self._request_with_retry('GET', url, timeout=60)
                content = resp.content
                if len(content) < 1024 or content[:5] != b'%PDF-':
                    fail += 1
                    print('       跳过{} (非有效PDF)'.format(pdfname))
                    continue
                with open(pdfpath, 'wb') as f:
                    f.write(content)
                success += 1
                print('       已成功下载{} ({:.1f}MB)'.format(pdfname, len(content) / 1024 / 1024))
            except Exception as e:
                fail += 1
                print('       下载失败: {}'.format(e))

        print('\n下载完成: 成功{}个, 跳过{}个, 失败{}个'.format(success, skip, fail))
