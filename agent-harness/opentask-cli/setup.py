"""OpenTask CLI - Setup configuration."""

from setuptools import setup, find_packages
import os

# 读取 README 文件
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()

setup(
    name='opentask',
    version='1.36.0',
    author='OpenTask Team',
    author_email='support@opentask.com',
    description='OpenTask CLI - AI Agent interface for OpenTask platform',
    long_description=read_file('CLI_README.md') if os.path.exists('CLI_README.md') else '',
    long_description_content_type='text/markdown',
    url='https://gitlab.example.com/opentask/agent-harness',
    project_urls={
        'Bug Tracker': 'https://gitlab.example.com/opentask/agent-harness/issues',
        'Source Code': 'https://gitlab.example.com/opentask/agent-harness',
        'Documentation': 'https://docs.opentask.com/cli',
    },

    packages=find_packages(where='.', exclude=['tests*', 'docs*', '*tests*']),

    # CLI 入口点
    entry_points={
        'console_scripts': [
            'opentask=opentask.opentask_cli:cli',
        ],
    },

    # Python 版本要求
    python_requires='>=3.7',

    # 包分类信息
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],

    # 关键词
    keywords='cli opentask ai agent productivity',

    # 包含的数据文件
    include_package_data=True,
    zip_safe=False,
)
