# Darjeeling

[![Build Status](https://travis-ci.org/squaresLab/Darjeeling.svg?branch=master)](https://travis-ci.org/squaresLab/Darjeeling)

Darjeeling is a work-in-progress language-independent automated program repair
tool. Unlike other repair tools such as GenProg, SPR, and Nopol, Darjeeling
delegates the responsibility of generating patches, obtaining coverage,
analysing code, and executing tests to other services. (For the most part, those
other services are also language independent.)
Once those auxillary concerns are removed, what is left is a lightweight
framework for composing and executing repair algorithms: Darjeeling.

## Features

* Multi-threaded asynchronous patch evaluation: maximises throughput by
  distributing patch evaluation across multiple threads using an asychronous
  queue.
* Test case reduction: test outcomes that can't be affected by a given patch,
  as determined by coverage information, are skipped during patch evaluation.

## Installation

We recommend that you use `pipenv` to install Darjeeling, although `pip3` or
`easy_install` may be used instead:

```
$ pipenv install darjeeling
```

Darjeeling supports Python >= 3.5.

## Usage

Provide a "Hello World" example.

## Configuration File Format

```
version: '1.0'
snapshot: 'manybugs:python:69223-69224'
seed: 0
localization:
  metric: tarantula
algorithm:
  type: random
optimizations:
  ignore-equivalent-prepends: yes
  ignore-dead-code: yes
  ignore-string-equivalent-snippets: yes
```

Below, we describe the top-level options exposed by the configuration file:

* :code:`version`: the version of the Darjeeling configuration file format
  that was used to write the file.
