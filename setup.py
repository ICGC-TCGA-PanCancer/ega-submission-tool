#!/usr/bin/env python
from setuptools import setup

setup(
    name = 'ega_sub',
    description = 'Python tool for assisting EGA metadata submission',
    packages=['ega_submission'],
    install_requires = ['Click', 'PyYAML'],
    entry_points={
        'console_scripts': [
            'ega_sub=ega_submission.cli:main',
        ]
    },
)