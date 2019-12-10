#!/usr/bin/env python
import os
from glob import glob
from setuptools import setup, find_packages


path = os.path.join(os.path.dirname(__file__), 'src/darjeeling/version.py')
with open(path, 'r') as f:
    exec(f.read())


setup(
    name='darjeeling',
    version=__version__,
    description='Distributed, language-independent, compositional search-based program repair',
    author='Chris Timperley',
    author_email='ctimperley@cmu.edu',
    url='https://github.com/squaresLab/Darjeeling',
    license='apache',
    python_requires='>=3.6',
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest'
    ],
    include_package_data=True,
    classifiers=[
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    entry_points={
        'console_scripts': [
            'darjeeling = darjeeling.cli:main',
        ]
    },
    test_suite='tests'
)
