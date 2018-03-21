#!/usr/bin/env python
from glob import glob
from setuptools import setup, find_packages

setup(
    name='darjeeling',
    version='0.0.1',
    description='Language-independent, distributed search-based program repair',
    long_description='TBA',
    author='Chris Timperley',
    author_email='ctimperley@cs.cmu.edu',
    url='https://github.com/squaresLab/Darjeeling',
    license='mit',
    install_requires=[
        'bugzoo',
        'requests',
        'flask'
    ],
    include_package_data=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
)
