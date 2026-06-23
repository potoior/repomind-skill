#!/usr/bin/env python3
"""Setup script for repomind package."""

from setuptools import setup, find_packages

setup(
    name="repomind",
    version="2.0.0",
    author="RepoMind Team",
    author_email="repomind@example.com",
    description="智能项目知识图谱生成工具 - 扫描代码仓库，提取实体和关系，生成知识图谱",
    long_description=open("readme.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/potoior/repomind-skill",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "git": ["gitpython>=3.1.0"],
        "all": ["gitpython>=3.1.0"],
    },
    entry_points={
        "console_scripts": [
            "repomind=repomind.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=["knowledge-graph", "code-analysis", "repository", "cli", "visualization"],
)
