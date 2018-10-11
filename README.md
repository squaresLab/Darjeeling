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
installed, and your user account must be a member of the `docker` group in
order [to avoid problems related to insufficient privileges](https://docs.docker.com/install/linux/linux-postinstall)
.

### Optional Extras

### Darjeeling

We recommend that you use `pipenv` to install Darjeeling, although `pip3` or
`easy_install` may be used instead:

```
$ pipenv install darjeeling
```

Darjeeling supports Python >= 3.5.

## Usage

Provide a "Hello World" example.
