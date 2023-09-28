#!/usr/bin/env python3

""" adrtools is a collection of various utilities for reading, parsing, and generating timeline data and files.

TODO: README

"""

from setuptools import setup

VER_MAJ = 0
VER_MIN = 0
VER_SUB = 1
VERSION = f"{VER_MAJ}.{VER_MIN}.{VER_SUB}"
PKG_DESC_SHORT = """
    adrtools is a collection of various utilities for reading, parsing, and generating timeline data and files.
"""

PKG_DESC_LONG = """
    TODO: Long description
"""


def setup_package():
    setup(
        name="adrtools",
        version=VERSION,
        url="https://github.com/SoulXP/adrtools",
        entry_points={
            'console_scripts': [
                'adr-pftscript2tsv = cltools.pftscript2tsv:main',
                'adr-pftgenspeakers = cltools.pftgenspeakers:main',
                'adr-pftgetcharacters = cltools.pftgetcharacters:main',
                'adr-mediaruntime = cltools.mediaruntime:main',
                'adr-mergecues = cltools.mergecues:main',
                'adr-cuedensity = cltools.cuedensity:main',
                'adr-worddensity = cltools.worddensity:main',
                'adr-characterdensity = cltools.characterdensity:main'
            ]
        },
        license="MIT",
        description=PKG_DESC_SHORT,
        long_description=PKG_DESC_LONG,
        long_description_content_type="text/markdown",
        author="Stefan Olivier",
        author_email="s.olivier1194@gmail.com",
        platforms=["Windows", "Linux", "Unix", "Mac OS-X"],
        install_requires=['docx', 'tableschema', 'fuzzywuzzy', 'pandas'],
        classifiers=[
            "Development Status :: 1 - Planning",
            "License :: OSI Approved :: MIT License",
            "Topic :: Text Processing",
            "Topic :: Utilities",
            "Topic :: Multimedia :: Sound/Audio :: Speech",
            "Programming Language :: Python :: 3.10"
        ]
    )


if __name__ == "__main__":
    setup_package()
    del setup
