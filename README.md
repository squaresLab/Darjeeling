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

### Prerequisites

To use Darjeeling, 
[Docker](https://docs.docker.com/install/linux/docker-ce/ubuntu) must be
installed on your machine, and your user account must be a member of the
`docker` group in order [to avoid problems related to insufficient privileges](https://docs.docker.com/install/linux/linux-postinstall)
.
Python 3.5 or greater and [pip3](https://pip.pypa.io/en/stable/installing/)
must also be installed; Darjeeling will not work with older versions of Python
3 nor will it work with any versions of Python 2.

### Optional Extras

We strongly recommend that you install either
[virtualenv](https://virtualenv.pypa.io/en/stable/) or
[pipenv](https://pipenv.readthedocs.io/en/latest/) to contain your installation
of Darjeeling and to avoid conflicting with system packages. Both of packages
can be installed via `pip` as follows:

```
$ pip install virtualenv
$ pip install pipenv
```

### Darjeeling

To install the latest stable release of Darjeeling from PyPI:

```
(venv) $ pipenv install darjeeling
```

Alternatively, to install from source, execute the following inside the virtual
environment:

```
(venv) $ pip install .
```

## Usage

Provide a "Hello World" example.
