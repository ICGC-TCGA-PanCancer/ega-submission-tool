#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name = 'ega_sub',
    description = 'Python tool for assisting EGA metadata submission',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires = ['Click', 'PyYAML', 'xmltodict'],
    entry_points={
        'console_scripts': [
            'ega_sub=ega_submission.cli:main',
        ]
    },
)