from pathlib import Path
from szreport.sz import SZ
import pandas as pd
from tqdm import tqdm
import time
sz = SZ()
cwd = r"E:\财报"

# 以万科A为例，股票代码000002，下载近10年年报
df= sz.companys()

df = df[df['code'].str.match('60')]
df=df[~df['name'].str.endswith('退')]

for code in tqdm(df['code'], desc="下载进度"):
    try:
        sz.download(code=code, savepath=cwd)
    except Exception as e:
        print(f"\n{code} 下载失败: {e}")
    time.sleep(0.5)


