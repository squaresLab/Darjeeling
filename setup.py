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
    long_description='TBA',
    author='Chris Timperley',
    author_email='ctimperley@cmu.edu',
    url='https://github.com/squaresLab/Darjeeling',
    license='mit',
    python_requires='>=3.5',
    install_requires=[
        'bugzoo>=2.1.7',
        'requests',
        'flask'
    ],
    include_package_data=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
)
