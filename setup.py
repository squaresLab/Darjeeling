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
    license='mit',
    python_requires='>=3.5',
    install_requires=[
        'bugzoo>=2.1.20',
        'rooibos>=0.3.0',
        'boggart>=0.1.16',
        'kaskara>=0.0.5',
        'attrs>=17.4.0',
        'cement>=3.0.0',
        'requests',
        'flask'
    ],
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest'
    ],
    include_package_data=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    classifiers=[
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
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
