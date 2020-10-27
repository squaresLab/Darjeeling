#!/usr/bin/env python
import os
from glob import glob
from setuptools import setup, find_packages


path = os.path.join(os.path.dirname(__file__), 'src/darjeeling/version.py')
with open(path, 'r') as f:
    exec(f.read())


setup(
    version=__version__,
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest'
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'darjeeling = darjeeling.cli:main',
        ]
    },
    test_suite='tests'
)
