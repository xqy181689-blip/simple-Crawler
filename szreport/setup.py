from setuptools import setup
import setuptools

setup(
    name='szreport',
    version='0.1.0',
    description='深圳证券交易所上市公司定期报告下载',
    author='',
    url='',
    packages=setuptools.find_packages(),
    install_requires=['requests', 'pandas'],
    python_requires='>=3.7',
    license="MIT",
    keywords=['深交所', 'SZSE', '定期报告', '年报下载', '金融', 'finance'],
)
