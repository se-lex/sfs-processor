#!/usr/bin/env python3
"""
Setup configuration for SFS Markdown Converter.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="sfs-md",
    version="1.0.0",
    description="Konverterare för Svenska författningssamlingen (SFS) till Markdown",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Martin",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "openai>=1.0.0",
        "pyyaml>=6.0",
        "click>=8.0.0",  # För bättre CLI-gränssnitt
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "sfs-download=sfs_md.cli.download:main",
            "sfs-process=sfs_md.cli.process:main",
            "sfs-fetch-new=sfs_md.cli.fetch_new:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Legal",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Text Processing :: Markup",
        "Topic :: Utilities",
    ],
)
