"""
SFS Markdown Converter

Ett Python-paket för att konvertera Svenska författningssamlingen (SFS) 
från JSON/HTML till Markdown-format med YAML frontmatter.
"""

__version__ = "1.0.0"
__author__ = "Martin"

from .core.processor import SFSProcessor
from .core.formatter import SFSFormatter
from .downloaders.riksdagen import RiksdagenDownloader
from .downloaders.rkrattsbaser import RkrattbaserDownloader

__all__ = [
    "SFSProcessor",
    "SFSFormatter", 
    "RiksdagenDownloader",
    "RkrattbaserDownloader",
]
