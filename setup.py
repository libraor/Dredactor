"""Dredactor包安装配置"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="dredactor",
    version="0.1.1",
    author="libraor",
    author_email="libraor@users.noreply.github.com",
    description="Word文档脱敏工具 - 强大的敏感信息识别与替换工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/libraor/Dredactor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
        "Topic :: Text Processing",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=[
        "python-docx>=1.1.0",
        "typer[all]>=0.12.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "web": ["streamlit>=1.28.0"],
        "ai": ["openai>=1.0.0"],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "pylint>=3.0.0",
            "mypy>=1.5.0",
            "streamlit>=1.28.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dredactor=dredactor.main:app",
        ],
    },
    package_data={
        "dredactor": [
            "rules/default_rules.json",
            "config/config.yaml",
        ],
    },
    include_package_data=True,
)
